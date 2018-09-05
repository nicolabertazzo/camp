from abc import ABCMeta, abstractmethod


class ABCCommand(object):

	__metaclass__ = ABCMeta

	@abstractmethod
	def execute(self):
		pass

	@property
	def status(self):
		return self._status

	@property
	def logs(self):
		return self._logs
	

class ABCRunner(object):

	__metaclass__ = ABCMeta

	@abstractmethod
	def run(self):
		pass

	@abstractmethod
	def get_result(self):
		pass