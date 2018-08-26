import operator
import inspect
import types

ops_signature = {
	(int, "+", int): int,
	(int, "-", int): int,
	(int, "*", int): int,
	(int, "//", int): int,
	(int, "%", int): int,
	(int, "<<", int): int,
	(int, ">>", int): int,
	(int, "&", int): int,
	(int, "|", int): int,
	(int, "^", int): int,
	(int, "==", int): bool,
	(int, "!=", int): bool,
	(int, "<", int): bool,
	(int, ">", int): bool,
	(int, "<=", int): bool,
	(int, ">=", int): bool,
	("-", int): int,
	("+", int): int,
	("~", int): int,
}

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
			res_type = ops_signature.get((self.type, text, other.type), any)
			return Deferred(Lambda(self, text, op, other), res_type)
		else:
			res_type = ops_signature.get((self.type, text, type(other)), any)
			defer = Deferred(self, res_type)
			defer.addPendingMath(text, op, other, reverse=False)
			return defer
	return infix

def rinfix(text, op):
	def rinfix(self, other):
		# Object . Deferred
		res_type = ops_signature.get((type(other), text, self.type), any)
		defer = Deferred(self, res_type)
		defer.addPendingMath(text, op, other, reverse=True)
		return defer
	return rinfix

def prefix(text, op):
	def prefix(self):
		res_type = ops_signature.get((text, self.type), any)
		return Deferred(Lambda(self, text, op), res_type)
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
	def __init__(self, f, tp=None):
		if isinstance(f, Deferred):
			self.f = f.f
			self.pending_math = [obj[:] for obj in f.pending_math]
			self.cached = f.cached
			self.cache = f.cache
			self.type = tp if tp is not None else f.type
		else:
			self.f = Lambda(f)
			self.pending_math = []
			self.cached = False
			self.cache = None
			self.type = tp if tp is not None else type(f)

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
			for optext, op, other, reverse in self.pending_math:
				if reverse:
					result = op(other, result)
				else:
					result = op(result, other)

			while isinstance(result, Deferred):
				result = result(context)
		finally:
			self.is_evaluating = False

		self.cached = True
		self.cache = result
		return result

	def addPendingMath(self, optext, op, other, reverse=False):
		if self.isA(int):
			if len(self.pending_math) > 0:
				last_optext = self.pending_math[-1][0]
				last_reverse = self.pending_math[-1][3]
				if last_optext == optext and not reverse and not last_reverse:
					if optext in ("+", ">>", "<<"):
						# Optimizable by sum
						self.pending_math[-1][2] += other
						return
					elif optext == "*":
						# Optimizable by multiplication
						self.pending_math[-1][2] *= other
						return
					elif optext == "&":
						# Optimizable by &
						self.pending_math[-1][2] &= other
						return
					elif optext == "|":
						# Optimizable by |
						self.pending_math[-1][2] &= other
						return
					elif optext == "^":
						# Optimizable by ^
						self.pending_math[-1][2] &= other
						return

			if not reverse and optext == "-":
				# Reverse -
				optext = "+"
				op = operator.add
				other = -other

		self.pending_math.append([optext, op, other, reverse])

	def isA(self, type):
		return (
			(
				self.type is not any and
				self.type is not Deferred.Raise and
				issubclass(self.type, type)
			)
		)

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

	__radd__ = rinfix("+", operator.add)
	__rsub__ = rinfix("-", operator.sub)
	__rmul__ = rinfix("*", operator.mul)
	__rdiv__ = rinfix("//", operator.truediv)
	__rfloordiv__ = rinfix("/", operator.floordiv)
	__rmod__ = rinfix("%", operator.mod)
	__rlshift__ = rinfix("<<", operator.lshift)
	__rrshift__ = rinfix(">>", operator.rshift)
	__rand__ = rinfix("&", operator.and_)
	__ror__ = rinfix("|", operator.or_)
	__rxor__ = rinfix("^", operator.xor)

	__neg__ = prefix("-", operator.neg)
	__pos__ = prefix("+", operator.pos)
	__invert__ = prefix("~", operator.invert)

	def __repr__(self):
		if self.repr_disabled:
			return "<Deferred>"

		rpr = repr(self.f)
		for optext, _, other, reverse in self.pending_math:
			if reverse:
				rpr = "({!r} {} {})".format(other, optext, rpr)
			else:
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
		return self.then(tp, tp)

	def then(self, f, tp):
		return Deferred(Lambda(self, "({})".format(f.__name__), lambda value: f(value)), tp)



	@classmethod
	def If(cls, cond, true, false):
		cond = cls(cond)
		true = cls(true)
		false = cls(false)

		ignore_true_type = true.type is Deferred.Raise
		ignore_false_type = false.type is Deferred.Raise
		if ignore_true_type:
			res_type = false.type
		elif ignore_false_type:
			res_type = true.type
		elif true.type is false.type:
			res_type = true.type
		else:
			res_type = any

		return cls(Lambda(
			lambda context: true(context) if cond(context) else false(context),
			lambda: "{!r} if {!r} else {!r}".format(true, cond, false)
		), res_type)

	@classmethod
	def Repeat(cls, count, what):
		count = cls(count)
		what = cls(what)

		def f(context):
			what1 = what(context)

			result = []
			for i in range(count(context)):
				result.append(what1)
			return result

		return cls(Lambda(f, lambda: "[{!r}] * {!r}".format(what, count)), list)

	@classmethod
	def Raise(cls, err):
		err = cls(err)
		def cb():
			raise err()
		return cls(Lambda(cb, lambda: "raise {!r}".format(err)), Deferred.Raise)


	@classmethod
	def And(cls, a, b):
		a = cls(a)
		b = cls(b)
		return cls(Lambda(a, "and", lambda a, b: a and b, b), bool)

	@classmethod
	def Or(cls, a, b):
		a = cls(a)
		b = cls(b)
		return cls(Lambda(a, "or", lambda a, b: a or b, b), bool)

	@classmethod
	def Same(cls, a, b, strict=False):
		# Returns True if a() will always be equal to b()
		if strict:
			if a is b:
				return True
		else:
			if not isinstance(a, Deferred) and not isinstance(b, Deferred):
				if a == b or a is b:
					return True

		a = cls(a)
		b = cls(b)

		if a.cached:
			a_value = a()
		elif isinstance(a.f, Lambda) and a.f.optext is None and not callable(a.f.l):
			a_value = a()
		else:
			return False

		if b.cached:
			b_value = b()
		elif isinstance(b.f, Lambda) and b.f.optext is None and not callable(b.f.l):
			b_value = b()
		else:
			return False

		if strict:
			return a_value is b_value
		else:
			return a_value == b_value or a_value is b_value