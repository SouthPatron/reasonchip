#!/usr/bin/env bash


python										\
	-m grpc_tools.protoc					\
	-I.										\
	--python_out=.							\
	--grpc_python_out=.						\
	--proto_path=. reasonchip.proto

