#!/usr/bin/env python3 
import lzss
import argparse

def main(filename, outputname):
	print(filename)
	lzss.encode_file(filename, outputname)



if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("UpdateImage", help="the path of the update image ")
	parser.add_argument("OutputImage", help="the output path of the compressed update image ")
	args = parser.parse_args()
	main(args.UpdateImage, args.OutputImage)


