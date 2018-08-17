import os
from .parser import Parser, EndOfParsingError


class Compiler:
	def __init__(self, syntax="py11", link=0o1000, file_list=[], project=None):
		self.syntax = syntax
		self.link_address = link
		self.file_list = file_list
		self.project = project

	def addFile(self, file):
		# Resolve file path
		if file.startswith("/") or file[1:3] == ":\\":
			# Absolute
			pass
		else:
			# Relative
			file = os.path.join(os.getcwd(), file)

		with open(file) as f:
			code = f.read()

		self.compileFile(file, code)


	def compileFile(self, file, code):
		parser = Parser(code)

		try:
			command = parser.parseCommand()
			print(command)
		except EndOfParsingError:
			return