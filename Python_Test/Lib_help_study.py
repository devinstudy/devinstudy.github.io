# coding = utf-8

"""
@author: DevinX

@file: Lib_help_study.py

@time: 2019/11/26 15:11

@desc:类帮助文档输出


"""
# from locust import HttpLocust,TaskSet,task,between
# import locust
import paramiko
import os,sys

class module_list():
	def __init__(self,class_name):
		self.frist_mod = ''
		self.out_list = []
		self.moudle_name = class_name
		self.filename = self.moudle_name + '.txt'

	def check_type_moduleN(self):
		'''
		判断库或者方法名类型为字符串还是列表
		根据不同类型，调用不同函数
		'''
		if isinstance(self.module_name,str):
			return module_list_file()
		else:
			return module_list_dir()

	def module_list_file(self):
		'''
		返回库的第一级方法列表，给列表解析方法
		当不为空时，库与方法名拼接成新列表，调用列表型函数
		'''
		try:
			out_ = dir(self.moudle_name)
		except ModuleNotFoundError as e:
			print('没有这个库，请确认后重试')
		else:
			# 输出正确的字符型库的dir内容到文件
			# file_name = self.moudle_name + '.txt'
			# with open(self.moudle_name,'a+') as f:
			# 	# str_ = sta_ = '[*]Dir===================='+self.moudle_name+'===================[*]\n'
			# 	o_ = self.str_  + str(out_)
			# 	f.write(o_)
			# 输出库的help内容到文件
			self.out_help(self.moudle_name)
			# 获取库的第一级方法列表
			for i in out_:
				o_2 = self.moudle_name +'.'+i
				self.out_list.append(o_2)
			return self.module_list_dir(self.out_list)



	def module_list_dir(self,olist):
		'''
		获取第三方库的第一方法列表，分别输出帮助文档
		'''
		for d in olist:
			self.out_help(d)

	def out_help(self,mname):
		# 导出函数的dir文档
		with open(self.filename,'a+') as f:
			# eof_ = '\n[*]Help==================='+mname+'===================[*]\n'
			sta_ = '[*]Dir===================='+mname+'===================[*]\n'
			mod_ = dir(mname)
			f.write(sta_)
			f.write(str(mod_))
		# 导出python函数帮助文档
		out =  sys.stdout
		sys.stdout = open(self.filename,'a+')
		print('\n[+]Help===================',mname,'===================[+]')
		help(mname)
		sys.stdout.close()
		sys.stdout = out

if __name__ == '__main__':
	# class_name = 'locust'
	class_name = 'paramiko'
	module_list(class_name).module_list_file()
	# out_list = ['locust.HttpLocust','locust.TaskSet','locust.task','locust.between']
	# out_help('help.txt','concurrent.futures.Future')
	# for out_ in out_list:
	# 	file_name = out_ + '.txt'
	# 	out_help(file_name,out_)
