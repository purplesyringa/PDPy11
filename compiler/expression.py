from .deferred import Deferred


class ExpressionEvaluateError(Exception):
	pass

class Expression:
	def __new__(cls, s):
		return Deferred(cls.Get(s))

	class Get:
		def __init__(self, s):
			self.s = s

		def __call__(self, compiler):
			if isinstance(self.s, int):
				# Integer
				return self.s
			elif isinstance(self.s, str) and self.s == ".":
				# . (dot)
				return compiler.PC
			else:
				# Label
				def label():
					try:
						return compiler.labels[self.s]
					except KeyError:
						raise ExpressionEvaluateError("Label '{}' not found".format(self.s))

				return Deferred(label)

		def deferredRepr(self):
			return "Expression({!r})".format(self.s)

	@staticmethod
	def asOffset(expr):
		expr.isOffset = True
		return expr