import socketio

BASE_URL = "http://127.0.0.1:8061"
TESTS_TRANSPORTS = ["polling"]


def main() -> None:
    sio = socketio.Client(logger=True, engineio_logger=True)

    sio.namespaces = ["/chat_v1"]

    sio.connect(
        BASE_URL,
        transports=TESTS_TRANSPORTS,
        namespaces="/chat_v1",
        headers={"smart-user-id": "abb10dda-8185-11e2-98b4-e41f13e6ace6"},
    )

    sio.sleep(1)

    sio.disconnect()


if __name__ == "__main__":
    main()
