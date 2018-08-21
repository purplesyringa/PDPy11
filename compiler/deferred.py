import operator
import inspect
import types

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
			return "({!r} {} {!r})".format(self.l, self.optext, self.r)
		elif self.op is not None:
			return "({}{!r})".format(self.optext, self.l)
		elif self.optext is not None:
			return "({})".format(self.optext)
		elif isinstance(self.l, Lambda):
			return repr(self.l)
		elif hasattr(self.l, "deferredRepr"):
			return self.l.deferredRepr()
		elif callable(self.l):
			return "{}()".format(self.l.__name__)
		else:
			return repr(self.l)

def infix(text, op):
	def infix(self, other):
		other = Deferred(other)
		return Deferred(Lambda(self, text, op, other))
	return infix

def infixi(text, op):
	def infixi(self, other):
		other = Deferred(other)
		self.f = Lambda(Deferred(self.f), text, op, other)
		return self
	return infixi

def prefix(text, op):
	def prefix(self):
		return Deferred(Lambda(self, text, op))
	return prefix

def convert(tp):
	def convert(self):
		return tp(self())
	return convert

def call(f, context):
	print("call", repr(f))
	spec = inspect.getargspec(f)
	args = len(spec.args)
	varargs = spec.varargs is not None
	kwargs = spec.keywords is not None

	# Method
	if isinstance(f, types.MethodType):
		args -= 1 # self
	elif isinstance(f, types.FunctionType):
		pass
	elif hasattr(f, "__call__"):
		# Callable object
		return call(f.__call__, context)

	if args >= 1 or varargs or kwargs:
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
	__eq__ = infix("==", operator.eq)
	__ne__ = infix("!=", operator.ne)
	__lt__ = infix("<", operator.lt)
	__gt__ = infix(">", operator.gt)
	__le__ = infix("<=", operator.le)
	__ge__ = infix(">=", operator.ge)

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


	def to(self, tp):
		assert isinstance(tp, type)
		return self.then(tp)

	def then(self, f):
		return Deferred(Lambda(self, "({})".format(f.__name__), lambda value: f(value)))


	@classmethod
	def If(cls, cond, true, false):
		cond = cls(cond)
		true = cls(true)
		false = cls(false)

		return cls(Lambda(
			lambda context: true(context) if cond(context) else false(context),
			"{!r} if {!r} else {!r}".format(true, cond, false)
		))

	@classmethod
	def Repeat(cls, count, what):
		count = cls(count)
		what = cls(what)

		def f(context):
			result = []
			for i in range(count(context)):
				result.append(what(context))
			return result

		return cls(f)

	@classmethod
	def Raise(cls, err):
		err = cls(err)
		def cb():
			raise err()
		return cls(Lambda(cb, "raise {!r}".format(err)))


	@classmethod
	def And(cls, a, b):
		a = cls(a)
		b = cls(b)
		return cls(Lambda(a, "and", lambda a, b: a and b, b))

	@classmethod
	def Or(cls, a, b):
		a = cls(a)
		b = cls(b)
		return cls(Lambda(a, "or", lambda a, b: a or b, b))