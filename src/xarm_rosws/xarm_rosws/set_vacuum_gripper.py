import rclpy
from rclpy.node import Node
from xarm_msgs.srv import VacuumGripperCtrl


class SetVacuumGripperClient(Node):
    def __init__(self):
        super().__init__('set_vacuum_gripper_client_async')
        self.c = self.create_client(VacuumGripperCtrl, '/ufactory/set_vacuum_gripper')
        while not self.c.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req = VacuumGripperCtrl.Request()

    def send_request(self, on: bool, wait: bool = False, timeout: float = 3.0, delay_sec: float = 0.0):
        self.req.on = on
        self.req.wait = wait
        self.req.timeout = timeout
        self.req.delay_sec = delay_sec
        self.future = self.c.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()
