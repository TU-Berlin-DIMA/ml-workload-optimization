from workload import Workload
import time


class mock_workload_3(Workload):
    def run(self, **args):
        time.sleep(5)
        return True
