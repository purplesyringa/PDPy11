from .deferred import Deferred


class Expression:
	def __new__(cls, s):
		return Deferred(cls.Get(s))

	class Get:
		def __init__(self, s):
			self.s = s

		def __call__(self):
			if self.s == ".":
				# . (dot)
				return context.PC
			elif isinstance(self.s, int):
				# Integer
				return self.s
			else:
				# Label
				return Deferred(context.labels[self.s])

		def deferredRepr(self):
			return "Expression({})".format(self.s)