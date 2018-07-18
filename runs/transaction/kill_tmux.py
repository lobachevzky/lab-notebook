from pathlib import PurePath

from runs.transaction.sub_transaction import SubTransaction


class InterruptTransaction(SubTransaction):
    def validate(self):
        self.ui.check_permission("Kill TMUX sessions for the following runs:",
                                 *self.queue)

    def process(self, path: PurePath):
        self.tmux(path).kill()
