import rclpy
from rclpy.node import Node
from xarm_msgs.srv import MoveCartesian


class SetPositionClient(Node):
    def __init__(self):
        super().__init__('set_position_client_async')
        self.c = self.create_client(MoveCartesian, '/ufactory/set_position')
        while not self.c.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req = MoveCartesian.Request()

    def send_request(self):
        self.req.pose = [250.0, 0.0, 250.0, 3.14, 0.0, 0.0]
        self.req.speed = 50.0
        self.req.acc = 500.0
        self.req.mvtime = 0.0

        self.future = self.c.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()


def main():
    rclpy.init()

    sic = SetPositionClient()
    response = sic.send_request()
    sic.get_logger().info(f"/ufactory/set_position: {response}")

    sic.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
