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
		else:
			return call(self.l, context)

	def __repr__(self):
		if self.r is not None:
			return "({!r} {} {!r})".format(self.l, self.getOpText(), self.r)
		elif self.op is not None:
			return "({}{!r})".format(self.getOpText(), self.l)
		elif self.optext is not None:
			return "({})".format(self.getOpText())
		elif isinstance(self.l, Lambda):
			return repr(self.l)
		elif hasattr(self.l, "deferredRepr"):
			return self.l.deferredRepr()
		elif callable(self.l):
			return "{}()".format(self.l.__name__)
		else:
			return repr(self.l)

	def getOpText(self):
		if callable(self.optext):
			return self.optext()
		else:
			return self.optext


def infix(text, op):
	def infix(self, other):
		if isinstance(other, Deferred):
			return Deferred(Lambda(self, text, op, other))
		else:
			defer = Deferred(self)
			defer.pending_math.append((text, op, other))
			return defer
	return infix

def prefix(text, op):
	def prefix(self):
		return Deferred(Lambda(self, text, op))
	return prefix

def convert(tp):
	def convert(self):
		return tp(self())
	return convert

def call(f, context):
	if not callable(f):
		return f

	if isinstance(f, Deferred):
		f.repr_disabled = True
	try:
		spec = inspect.getargspec(f)
	except TypeError:
		spec = inspect.getargspec(f.__call__)
	finally:
		if isinstance(f, Deferred):
			f.repr_disabled = False

	args = len(spec.args)
	varargs = spec.varargs is not None
	kwargs = spec.keywords is not None

	# Method
	if isinstance(f, types.MethodType):
		args -= 1 # self
	elif isinstance(f, types.FunctionType):
		pass

	if args >= 1 or varargs or kwargs:
		return f(context)
	else:
		return f()


class Deferred(object):
	def __init__(self, f):
		if isinstance(f, Deferred):
			self.f = f.f
			self.pending_math = f.pending_math[:]
		else:
			self.f = Lambda(f)
			self.pending_math = []

		self.cached = False
		self.cache = None
		self.is_evaluating = False
		self.repr_disabled = False


	def __call__(self, context=None):
		if self.cached:
			return self.cache
		elif self.is_evaluating:
			raise OverflowError("Deferred value is recursively defined")

		self.is_evaluating = True

		try:
			result = self.f(context)
			# Handle padding math
			for optext, op, other in self.pending_math:
				result = op(result, other)

			while isinstance(result, Deferred):
				result = result(context)
		finally:
			self.is_evaluating = False

		self.cached = True
		self.cache = result
		return result

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

	__neg__ = prefix("-", operator.neg)
	__pos__ = prefix("+", operator.pos)
	__invert__ = prefix("~", operator.invert)

	def __repr__(self):
		if self.repr_disabled:
			return "<Deferred>"

		rpr = repr(self.f)
		for optext, _, other in self.pending_math:
			rpr = "({} {} {!r})".format(rpr, optext, other)
		return rpr

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
			lambda: "{!r} if {!r} else {!r}".format(true, cond, false)
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
		return cls(Lambda(cb, lambda: "raise {!r}".format(err)))


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