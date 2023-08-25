from __future__ import division
import pyparsing as pyp
import math
import operator

# Helper function for counting game to convert word to number
# Source: https://stackoverflow.com/questions/493174/is-there-a-way-to-convert-number-words-to-integers
def word_to_int(textnum, numwords={}):
    if not numwords:
      units = [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen",
      ]

      tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

      scales = ["hundred", "thousand", "million", "billion", "trillion"]

      numwords["and"] = (1, 0)
      for idx, word in enumerate(units):    numwords[word] = (1, idx)
      for idx, word in enumerate(tens):     numwords[word] = (1, idx * 10)
      for idx, word in enumerate(scales):   numwords[word] = (10 ** (idx * 3 or 2), 0)

    current = result = 0
    for word in textnum.split():
        if word not in numwords:
          raise Exception("Illegal word: " + word)

        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0

    return result + current

# Helper function for counting game to convert math equations to number
# Source: https://stackoverflow.com/questions/11951701/safe-way-to-parse-user-supplied-mathematical-formula-in-python
class NumericStringParser(object):
	def pushFirst(self, strg, loc, toks ):
		self.exprStack.append( toks[0] )
	def pushUMinus(self, strg, loc, toks ):
		if toks and toks[0] == '-':
			self.exprStack.append( 'unary -' )
	def __init__(self):
		"""
		expop   :: '^'
		multop  :: '*' | '/'
		addop   :: '+' | '-'
		integer :: ['+' | '-'] '0'..'9'+
		atom    :: PI | E | real | fn '(' expr ')' | '(' expr ')'
		factor  :: atom [ expop factor ]*
		term    :: factor [ multop factor ]*
		expr    :: term [ addop term ]*
		"""
		point = pyp.Literal( "." )
		e     = pyp.CaselessLiteral( "E" )
		fnumber = pyp.Combine( pyp.Word( "+-"+pyp.nums, pyp.nums ) + 
						   pyp.Optional( point + pyp.Optional( pyp.Word( pyp.nums ) ) ) +
						   pyp.Optional( e + pyp.Word( "+-"+pyp.nums, pyp.nums ) ) )
		ident = pyp.Word(pyp.alphas, pyp.alphas+pyp.nums+"_$")       
		plus  = pyp.Literal( "+" )
		minus = pyp.Literal( "-" )
		mult  = pyp.Literal( "x" )
		div   = pyp.Literal( "/" )
		lpar  = pyp.Literal( "(" ).suppress()
		rpar  = pyp.Literal( ")" ).suppress()
		addop  = plus | minus
		multop = mult | div
		expop = pyp.Literal( "^" )
		pi    = pyp.CaselessLiteral( "PI" )
		expr = pyp.Forward()
		atom = ((pyp.Optional(pyp.oneOf("- +")) +
				 (pi|e|fnumber|ident+lpar+expr+rpar).setParseAction(self.pushFirst))
				| pyp.Optional(pyp.oneOf("- +")) + pyp.Group(lpar+expr+rpar)
				).setParseAction(self.pushUMinus)       
		# by defining exponentiation as "atom [ ^ factor ]..." instead of 
		# "atom [ ^ atom ]...", we get right-to-left exponents, instead of left-to-right
		# that is, 2^3^2 = 2^(3^2), not (2^3)^2.
		factor = pyp.Forward()
		factor << atom + pyp.ZeroOrMore( ( expop + factor ).setParseAction(
			self.pushFirst ) )
		term = factor + pyp.ZeroOrMore( ( multop + factor ).setParseAction(
			self.pushFirst ) )
		expr << term + pyp.ZeroOrMore( ( addop + term ).setParseAction( self.pushFirst ) )
		self.bnf = expr
		# map operator symbols to corresponding arithmetic operations
		epsilon = 1e-12
		self.opn = { "+" : operator.add,
				"-" : operator.sub,
				"x" : operator.mul,
				"/" : operator.truediv,
				"^" : operator.pow }
		self.fn  = { "sin" : math.sin,
				"cos" : math.cos,
				"tan" : math.tan,
				"abs" : abs,
				"sqrt": math.sqrt,
				"ln"  : math.log}
		self.exprStack = []
	def evaluateStack(self, s ):
		op = s.pop()
		if op == 'unary -':
			return -self.evaluateStack( s )
		if op in "+-x/^":
			op2 = self.evaluateStack( s )
			op1 = self.evaluateStack( s )
			return self.opn[op]( op1, op2 )
		elif op == "PI":
			return math.pi # 3.1415926535
		elif op == "E":
			return math.e  # 2.718281828
		elif op in self.fn:
			return self.fn[op]( self.evaluateStack( s ) )
		elif op[0].isalpha():
			return 0
		else:
			return float( op )
	def eval(self, num_string, parseAll = True):
		self.exprStack = []
		results = self.bnf.parseString(num_string, parseAll)
		val = self.evaluateStack( self.exprStack[:] )
		return int(round(val))