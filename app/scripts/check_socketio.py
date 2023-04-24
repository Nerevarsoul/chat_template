import socketio

from app.sio.constants import NAMESPACE, USER_HEADER_NAME

BASE_URL = "http://127.0.0.1:8081"
TESTS_TRANSPORTS = ["polling"]


def main():
    sio = socketio.Client(logger=True, engineio_logger=True)

    sio.namespaces = [NAMESPACE]

    sio.connect(
        BASE_URL,
        transports=TESTS_TRANSPORTS,
        namespaces=NAMESPACE,
        headers={USER_HEADER_NAME: "abb10dda-8185-11e2-98b4-e41f13e6ace6"},
    )

    sio.sleep(1)

    sio.disconnect()


if __name__ == "__main__":
    main()
