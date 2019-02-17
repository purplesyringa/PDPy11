from .deferred import Deferred
from .util import octal, raiseExpressionEvaluateError


class Expression(object):
	def __new__(cls, s, file_id, line, column):
		if isinstance(s, int):
			return s
		else:
			return Deferred(cls.Get(s, file_id, line, column), int)

	class Get(object):
		def __init__(self, s, file_id, line, column):
			self.s = s
			self.file_id = file_id
			self.line = line
			self.column = column

		def __call__(self, compiler):
			if isinstance(self.s, int):
				return self.s

			def label():
				try:
					return compiler.labels[self.s]
				except KeyError:
					try:
						global_s = "{file_id}:{s}".format(file_id=self.file_id, s=self.s)
						return compiler.labels[global_s]
					except KeyError:
						raiseExpressionEvaluateError(
							self.file_id,
							self.line,
							self.column,
							"Label '{s}' not found".format(s=self.s)
						)

			return Deferred(label, int)

		def deferredRepr(self):
			if self.s[0] in "0123456789":
				return "Label({s})".format(s=self.s)
			else:
				return self.s

		def map(self, f):
			if isinstance(self.s, int):
				return self
			return Expression.Get(f(self.s), self.file_id, self.line, self.column)

	@staticmethod
	def asOffset(expr):
		if isinstance(expr, int):
			expr = Deferred(Expression.Get(expr, "???", 0, 0), int)

		expr.isOffset = True
		return expr


class StaticAlloc(object):
	def __new__(cls, length, is_byte):
		return Deferred(cls.Get(length, is_byte), int)

	class Get(object):
		def __init__(self, length, is_byte):
			self.length = length
			if is_byte:
				self.byte_length = length + length % 2
			else:
				self.byte_length = length * 2
			self.is_byte = is_byte

			self.cache = None

		def __call__(self, compiler):
			if self.cache is None:
				self.cache = compiler.static_alloc(self.byte_length)
			return self.cache

		def deferredRepr(self):
			if self.is_byte:
				return "STATIC_ALLOC_BYTE({length!r})".format(length=self.length)
			else:
				return "STATIC_ALLOC({length!r})".format(length=self.length)