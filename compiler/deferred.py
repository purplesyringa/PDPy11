import operator
import inspect

class Lambda(object):
	def __init__(self, l, optext=None, op=None, r=None):
		self.l = l
		self.optext = optext
		self.op = op
		self.r = r
	def __call__(self, context):
		if self.r is not None:
			return self.op(call(self.l, context), call(self.r, context))
		elif self.op is not None:
			return self.op(call(self.l, context))
		elif callable(self.l):
			return call(self.l, context)
		else:
			return self.l
	def __repr__(self):
		if self.r is not None:
			return "(%r %s %r)" % (self.l, self.optext, self.r)
		elif self.op is not None:
			return "(%s%r)" % (self.optext, self.l)
		elif isinstance(self.l, Lambda):
			return repr(self.l)
		elif hasattr(self.l, "deferredRepr"):
			return self.l.deferredRepr()
		elif callable(self.l):
			return "%s()" % self.l.__name__
		else:
			return repr(self.l)

def infix(text, op):
	def infix(self, other):
		self = Deferred(self)
		other = Deferred(other)
		return Deferred(Lambda(self, text, op, other))
	return infix

def infixi(text, op):
	def infixi(self, other):
		self = Deferred(self)
		other = Deferred(other)
		oldf = self.f
		self.f = Lambda(Deferred(oldf), text, op, other)
		return self
	return infixi

def prefix(text, op):
	def prefix(self):
		self = Deferred(self)
		return Deferred(Lambda(self, text, op))
	return prefix

def convert(tp):
	def convert(self):
		return tp(self())
	return convert

def call(f, context):
	spec = inspect.getargspec(f)
	varargs = spec.varargs is not None
	kwargs = spec.keywords is not None

	if len(spec.args) or varargs or kwargs:
		return f(context)
	else:
		return f()


class Deferred(object):
	def __init__(self, f):
		if isinstance(f, Deferred):
			self.f = f.f
		else:
			self.f = Lambda(f)

	def __call__(self, context=None):
		return self.f(context)

	__add__ = infix("+", operator.add)
	__sub__ = infix("-", operator.sub)
	__mul__ = infix("*", operator.mul)
	__div__ = infix("//", operator.truediv)
	__floordiv__ = infix("/", operator.floordiv)
	__mod__ = infix("%", operator.mod)
	__lshift__ = infix("<<", operator.lshift)
	__rshift__ = infix(">>", operator.rshift)
	__and__ = infix("&", operator.and_)
	__or__ = infix("|", operator.or_)
	__xor__ = infix("^", operator.xor)

	__radd__ = infix("+", operator.add)
	__rsub__ = infix("-", operator.sub)
	__rmul__ = infix("*", operator.mul)
	__rdiv__ = infix("//", operator.truediv)
	__rfloordiv__ = infix("/", operator.floordiv)
	__rmod__ = infix("%", operator.mod)
	__rlshift__ = infix("<<", operator.lshift)
	__rrshift__ = infix(">>", operator.rshift)
	__rand__ = infix("&", operator.and_)
	__ror__ = infix("|", operator.or_)
	__rxor__ = infix("^", operator.xor)

	__iadd__ = infixi("+", operator.add)
	__isub__ = infixi("-", operator.sub)
	__imul__ = infixi("*", operator.mul)
	__idiv__ = infixi("//", operator.truediv)
	__ifloordiv__ = infixi("/", operator.floordiv)
	__imod__ = infixi("%", operator.mod)
	__ilshift__ = infixi("<<", operator.lshift)
	__irshift__ = infixi(">>", operator.rshift)
	__iand__ = infixi("&", operator.and_)
	__ior__ = infixi("|", operator.or_)
	__ixor__ = infixi("^", operator.xor)

	__neg__ = prefix("-", operator.neg)
	__pos__ = prefix("+", operator.pos)
	__invert__ = prefix("~", operator.invert)

	def __repr__(self):
		return repr(self.f)

	__int__ = convert(int)
	__str__ = convert(str)
	__float__ = convert(float)
	__complex__ = convert(complex)

	def __getitem__(self, name):
		return self()[name]
	def __setitem__(self, name, value):
		self()[name] = value


	def to(self, type):
		self = Deferred(self)
		return Deferred(lambda context: type(self(context)))


	@classmethod
	def If(cls, cond, true, false):
		cond = cls(cond)
		true = cls(true)
		false = cls(false)

		return cls(lambda context: true(context) if cond(context) else false(context))

	@classmethod
	def Raise(cls, err):
		err = cls(err)
		def cb():
			raise err()
		return cls(cb)


	@classmethod
	def And(cls, a, b):
		a = cls(a)
		b = cls(b)
		return cls(lambda: a(context) and b(context))

	@classmethod
	def Or(cls, a, b):
		a = cls(a)
		b = cls(b)
		return cls(lambda: a(context) or b(context))