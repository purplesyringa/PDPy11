from .deferred import Deferred


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
				return Deferred(lambda: compiler.labels[self.s])

		def deferredRepr(self):
			return "Expression({!r})".format(self.s)
		def isReady(self):
			return isinstance(self.s, int)

	@staticmethod
	def asOffset(expr):
		expr.isOffset = True
		return expr