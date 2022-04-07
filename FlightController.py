import time
from SerCom32 import SerCom32
import threading
from logger import logger, Exception_Catcher
import re

logger.set_level("DEBUG")


class FlightController:
    _start_bit = [0xAA, 0x22]
    _stop_bit = []

    def __init__(self) -> None:
        self.running = True
        self.connected = False
        self.ser = SerCom32("/dev/serial0", 115200)
        logger.info("FC: Serial port opened")
        self.set_option(0)
        self.read_thread = threading.Thread(target=self._read_serial_task)
        self.read_thread.start()
        self.update_thread = threading.Thread(target=self._update_state_task)
        self.update_thread.start()
        self.show_thread = None
        self.drone_state = {
            "flying": False,
            "alt_hold": False,
            "loc_hold": False,
            "height": 0,
            "heading": 0,
            "spd_x": 0,
            "spd_y": 0,
            "spd_z": 0,
            "spd_rad": 0,
        }

    def quit(self) -> None:
        self.running = False
        self.read_thread.join()
        self.update_thread.join()
        if self.show_thread is not None:
            self.show_thread.join()
        self.ser.close()
        logger.info("FC: Threads closed, FC offline")

    def set_option(self, option: int) -> None:
        self.ser.sendConfig(
            startBit=FlightController._start_bit,
            optionBit=[option],
            stopBit=FlightController._stop_bit,
            useSumCheck=False,
        )

    def send_form_data(self, data: list, option: int) -> None:
        self.set_option(option)
        _ = self.ser.send_form_data(data)
        logger.debug(f"FC: Send: {data}")

    def wait_for_connect(self, timeout=-1) -> bool:
        t0 = time.time()
        logger.info("FC: Waiting for FC connection")
        while True:
            if timeout > 0 and time.time() - t0 > timeout:
                logger.error("FC: Wait for connect timeout")
                return False
            self.send_form_data([0x01], 0)
            time.sleep(0.5)
            if self.connected:
                logger.info("FC: Connected")
                return True
            time.sleep(0.5)

    def _read_serial_task(self):
        logger.info("FC: Read thread started")
        self.ser.read_serial()
        self.ser.rx_data()
        while self.running:
            try:
                self.ser.read_serial()
            except Exception as e:
                logger.error(f"FC: Read thread exception: {e}")

    def _update_state_task(self):
        def is_number(n):
            is_num = True
            try:
                num = float(n)
                is_num = num == num
            except ValueError:
                is_num = False
            return is_num
        logger.info("FC: Update state thread started")
        while self.running:
            try:
                if self.ser.rx_done():
                    s = self.ser.rx_data().decode("utf-8")
                    # logger.debug(f"FC: Recv: {s}")
                    spl = [x.strip() for x in s.split(',')]
                    find = [x for x in spl if is_number(x)]
                    if find != []:
                        if len(find) == 9:
                            n = 0
                            for key in self.drone_state:
                                if key == "flying" or key == "alt_hold" or key == "loc_hold":
                                    self.drone_state[key] = bool(int(find[n]))
                                else:
                                    self.drone_state[key] = float(find[n])
                                n += 1
                            # logger.debug("FC: Update state: " + str(self.drone_state))
                            self.connected = True
            except Exception as e:
                logger.error(f"FC: Update state thread exception: {e}")

    def _show_state_task(self):
        while self.running:
            state = [f"{key}:{value:6.02f}   " for key, value in self.drone_state.items()]
            str_state = " ".join(state)
            print(f"{str_state}\r", end="")
            
    def active_show_state(self):
        self.show_thread = threading.Thread(target=self._show_state_task)
        self.show_thread.start()
        
    def manual_control(self):
        import tty
        import sys
        import termios
        orig_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin)
        while self.running:
            k = ord(sys.stdin.read(1))
            if k == 27:
                logger.info("FC: ESC pressed, exit")
                self.quit()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, orig_settings)
            
if __name__ == "__main__":
    fc = FlightController()
    fc.wait_for_connect(1)
    fc.active_show_state()
    fc.manual_control()
