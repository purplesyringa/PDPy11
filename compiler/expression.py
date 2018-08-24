from .deferred import Deferred
from .util import octal


class ExpressionEvaluateError(Exception):
	pass

class Expression(object):
	def __new__(cls, s, file_id):
		return Deferred(cls.Get(s, file_id), int)

	class Get(object):
		def __init__(self, s, file_id):
			self.s = s
			self.file_id = file_id

		def __call__(self, compiler):
			if isinstance(self.s, int):
				# Integer
				return self.s
			else:
				# Label
				def label():	
					try:
						return compiler.labels[self.s]
					except KeyError:
						try:
							global_s = "{}:{}".format(self.file_id, self.s)
							return compiler.labels[global_s]
						except KeyError:
							raise ExpressionEvaluateError("Label '{}' not found".format(self.s))

				return Deferred(label, int)

		def deferredRepr(self):
			if isinstance(self.s, int):
				return octal(self.s)
			elif self.s[0] in "0123456789":
				return "Label({})".format(self.s)
			else:
				return self.s

	@staticmethod
	def asOffset(expr):
		expr.isOffset = True
		return expr