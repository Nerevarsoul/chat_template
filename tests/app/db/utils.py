import inspect
from typing import Any, Callable, List, Optional

import factory
import factory.fuzzy
from factory.alchemy import base
from factory.builder import (
    BuildStep,
    DeclarationSet,
    Resolver,
    StepBuilder,
    parse_declarations,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession


class AsyncSQLAlchemyOptions(base.FactoryOptions):
    def _build_default_options(self) -> List[base.OptionDefault]:
        options: List[base.OptionDefault] = super()._build_default_options()
        options.extend(
            [
                base.OptionDefault("async_alchemy_get_or_create", (), inherit=True),
                base.OptionDefault("sqlalchemy_session", None, inherit=True),
            ]
        )
        return options


class AsyncBuildStep(BuildStep):
    async def resolve(self, declarations: DeclarationSet) -> None:
        self.stub = Resolver(declarations=declarations, step=self, sequence=self.sequence)
        for field_name in declarations:
            if isinstance(declarations[field_name].declaration, factory.SubFactory):
                attr = getattr(self.stub, field_name)
                if inspect.isawaitable(attr):
                    attr = await attr
                self.attributes[field_name] = attr
                self.stub._Resolver__values[field_name] = attr

        for field_name in declarations:
            self.attributes[field_name] = getattr(self.stub, field_name)


class AsyncStepBuilder(StepBuilder):
    async def build(self, parent_step: Optional[BuildStep] = None, force_sequence: Any = None) -> Any:
        pre, post = parse_declarations(
            self.extras,
            base_pre=self.factory_meta.pre_declarations,
            base_post=self.factory_meta.post_declarations,
        )

        if force_sequence is not None:
            sequence = force_sequence
        elif self.force_init_sequence is not None:
            sequence = self.force_init_sequence
        else:
            sequence = self.factory_meta.next_sequence()

        step = AsyncBuildStep(builder=self, sequence=sequence, parent_step=parent_step)
        await step.resolve(pre)

        args, kwargs = self.factory_meta.prepare_arguments(step.attributes)

        instance = await self.factory_meta.instantiate(step=step, args=args, kwargs=kwargs)

        postgen_results = {}
        for declaration_name in post.sorted():
            declaration = post[declaration_name]
            declaration_result = declaration.declaration.evaluate_post(
                instance=instance, step=step, overrides=declaration.context
            )
            if inspect.isawaitable(declaration_result):
                declaration_result = await declaration_result
            postgen_results[declaration_name] = declaration_result

        self.factory_meta.use_postgeneration_results(instance=instance, step=step, results=postgen_results)
        return instance


class AsyncSQLAlchemyFactory(factory.Factory):
    _options_class = AsyncSQLAlchemyOptions

    @classmethod
    async def _generate(cls, strategy: Any, params: Any) -> Any:
        cls._original_params = params
        if cls._meta.abstract:
            raise factory.errors.FactoryError(
                f"Cannot generate instances of abstract factory {cls.__name__}; "
                f"Ensure {cls.__name__}.Meta.model is set and {cls.__name__}.Meta.abstract "
                "is either not set or False."
            )

        step = AsyncStepBuilder(cls._meta, params, strategy)
        return await step.build()

    @classmethod
    async def _get_or_create(
        cls, model_class: Any, session: Callable[..., AsyncSession], args: Any, kwargs: Any
    ) -> Any:
        key_fields = {}
        for field in cls._meta.async_alchemy_get_or_create:
            if field not in kwargs:
                raise factory.alchemy.errors.FactoryError(
                    "async_alchemy_get_or_create - "
                    f"Unable to find initialization value for '{field}' in factory {cls.__name__}"
                )
            key_fields[field] = kwargs.pop(field)

        async with session() as db_session:
            obj = (
                (await db_session.execute(select(model_class).filter_by(*args, **key_fields))).scalars().one_or_none()
            )

        if not obj:
            obj = await cls._save(model_class, session, args, {**key_fields, **kwargs})
        return obj

    @classmethod
    async def _create(cls, model_class: Any, *args: Any, **kwargs: Any) -> Any:
        session_provider = cls._meta.sqlalchemy_session
        if session_provider is None:
            raise RuntimeError("No async sqlalchemy session factory provided")

        session = session_provider()
        if cls._meta.async_alchemy_get_or_create:
            return await cls._get_or_create(model_class, session, args, kwargs)
        return await cls._save(model_class, session, args, kwargs)

    @classmethod
    async def create(cls, **kwargs: Any) -> Any:
        return await cls._generate(factory.base.enums.CREATE_STRATEGY, kwargs)

    @classmethod
    async def _build(cls, model_class: Any, *args: Any, **kwargs: Any) -> Any:
        return model_class(*args, **kwargs)

    @classmethod
    async def build(cls, **kwargs: Any) -> Any:
        return await cls._generate(factory.base.enums.BUILD_STRATEGY, kwargs)

    @classmethod
    async def _save(cls, model_class: Any, session: Callable[..., AsyncSession], args: Any, kwargs: Any) -> Any:
        async with session() as db_session:
            obj = model_class(*args, **kwargs)
            db_session.add(obj)
            await db_session.commit()
        return obj
