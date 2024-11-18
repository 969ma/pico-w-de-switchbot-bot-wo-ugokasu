import ubluetooth
import ubinascii
from micropython import const
import machine
import time
import sys
import json

botMacAddress = "cc1234567890"

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(13)
_IRQ_GATTC_DESCRIPTOR_DONE = const(14)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)
_IRQ_GATTC_INDICATE = const(19)
_IRQ_GATTS_INDICATE_DONE = const(20)
_IRQ_MTU_EXCHANGED = const(21)
_IRQ_L2CAP_ACCEPT = const(22)
_IRQ_L2CAP_CONNECT = const(23)
_IRQ_L2CAP_DISCONNECT = const(24)
_IRQ_L2CAP_RECV = const(25)
_IRQ_L2CAP_SEND_READY = const(26)
_IRQ_CONNECTION_UPDATE = const(27)
_IRQ_ENCRYPTION_UPDATE = const(28)
_IRQ_GET_SECRET = const(29)
_IRQ_SET_SECRET = const(30)

led = machine.Pin("LED", machine.Pin.OUT)
led.on()

ble = ubluetooth.BLE()
ble.active(True)

botFound = False
endFlag = False
valueHandleWrite = 0  # 19が毎回入る
bleDevice = {"addr_type": "", "addr": "", "adv_type": "", "rssi": "", "adv_data": "", "conn_handle": ""}


def bt_irq(event, data):
    if event == _IRQ_SCAN_RESULT:  # デバイス発見のたびに呼ばれる
        addr_type, addr, adv_type, rssi, adv_data = data
        print(f"Address Type: {addr_type}, Address: {ubinascii.hexlify(addr)}, Advertisement Type: {adv_type}, RSSI: {rssi} dBm, Advertisement Data: {ubinascii.hexlify(adv_data)}")

        if botMacAddress == bytes(addr).hex():
            global botFound
            botFound = True

            bleDevice["addr_type"] = addr_type
            bleDevice["addr"] = addr
            bleDevice["adv_type"] = adv_type
            bleDevice["rssi"] = rssi
            bleDevice["adv_data"] = ubinascii.hexlify(adv_data)

            # スキャンを終了
            ble.gap_scan(None)
    elif event == _IRQ_SCAN_DONE:  # デバイスのスキャンが終わったら呼ばれる
        print("スキャン完了")
        if botFound:
            print("botが見つかりました")

            print(bleDevice)
            ble.gap_connect(bleDevice["addr_type"], bleDevice["addr"])
        else:
            print("botが見つかりませんでした")

            global endFlag
            endFlag = True
        pass

    elif event == _IRQ_PERIPHERAL_CONNECT:  # デバイスと接続したら呼ばれる
        conn_handle, addr_type, addr = data

        print("Connected")
        bleDevice["conn_handle"] = conn_handle

        # Serviceを探す
        ble.gattc_discover_services(conn_handle)

    elif event == _IRQ_GATTC_SERVICE_RESULT:
        conn_handle, start_handle, end_handle, uuid = data

        # ServiceのUUID
        if uuid == ubluetooth.UUID("cba20d00-224d-11e6-9fb8-0002a5d5c51b"):
            pass

    elif event == _IRQ_GATTC_SERVICE_DONE:
        conn_handle, status = data
        print("Service Done")

        # Characteristicsを探す
        ble.gattc_discover_characteristics(conn_handle, 1, 0xffff)

    elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:  # Charactaristicが見つかるたびに呼ばれる
        conn_handle, def_handle, value_handle, properties, uuid = data

        if uuid == ubluetooth.UUID("cba20002-224d-11e6-9fb8-0002a5d5c51b"):  # 書き込みのCharacteristicのUUID
            global valueHandleWrite
            valueHandleWrite = value_handle

    elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:  # Charactaristicのスキャンが終わったら呼ばれる
        conn_handle, status = data
        print("Charactaristic Done")

        # 指示を送信(アームを動かす)
        ble.gattc_write(conn_handle, valueHandleWrite, b"\x57\x01\x00", 1)

    elif event == _IRQ_GATTC_WRITE_DONE:  # 送信が終わったら呼ばれる
        conn_handle, value_handle, status = data
        print("Write Done")

    elif event == _IRQ_GATTC_NOTIFY:  # データを受信したら呼ばれる
        conn_handle, value_handle, notify_data = data
        print("NOTIFY!!")
        print(ubinascii.hexlify(notify_data))

        if ubinascii.hexlify(notify_data) == b"01ff00":
            print("Success!!")

        # 切断
        ble.gap_disconnect(conn_handle)

    elif event == _IRQ_PERIPHERAL_DISCONNECT:  # 切断されたときに呼ばれる
        conn_handle, addr_type, addr = data
        print("Disconencted")

        global endFlag
        endFlag = True


ble.irq(bt_irq)
ble.gap_scan(1000, 1000000, 1000000, False)

# BLEが動作しているときに終了するとエラーがでるため、ループで待機しておく
while not endFlag:
    time.sleep(1)

# BLE終了
# ble.active(False)
