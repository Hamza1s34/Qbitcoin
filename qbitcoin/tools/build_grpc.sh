#!/usr/bin/env bash
pushd . > /dev/null
cd $( dirname "${BASH_SOURCE[0]}" )
cd ..

python -m grpc_tools.protoc -I=protos --python_out=generated --grpc_python_out=generated protos/qbit.proto
python -m grpc_tools.protoc -I=protos/qbit.proto -I=protos --python_out=generated --grpc_python_out=generated protos/qbitlegacy.proto
python -m grpc_tools.protoc -I=protos --python_out=generated --grpc_python_out=generated protos/qbitbase.proto
python -m grpc_tools.protoc -I=protos --python_out=generated --grpc_python_out=generated protos/qbitmining.proto
python -m grpc_tools.protoc -I=protos --python_out=generated --grpc_python_out=generated protos/qbitdebug.proto
python -m grpc_tools.protoc -I=protos --python_out=generated --grpc_python_out=generated protos/qbitstateinfo.proto
python -m grpc_tools.protoc -I=protos --python_out=generated --grpc_python_out=generated protos/qbitwallet.proto

# Patch import problem in generated code
sed -i 's|import qbit_pb2 as qbit__pb2|import qbitcoin.generated.qbit_pb2 as qbit__pb2|g' generated/qbit_pb2_grpc.py
sed -i 's|import qbit_pb2 as qbit__pb2|import qbitcoin.generated.qbit_pb2 as qbit__pb2|g' generated/qbitlegacy_pb2.py
sed -i 's|import qbit_pb2 as qbit__pb2|import qbitcoin.generated.qbit_pb2 as qbit__pb2|g' generated/qbitmining_pb2.py
sed -i 's|import qbit_pb2 as qbit__pb2|import qbitcoin.generated.qbit_pb2 as qbit__pb2|g' generated/qbitdebug_pb2.py
sed -i 's|import qbit_pb2 as qbit__pb2|import qbitcoin.generated.qbit_pb2 as qbit__pb2|g' generated/qbitstateinfo_pb2.py
sed -i 's|import qbit_pb2 as qbit__pb2|import qbitcoin.generated.qbit_pb2 as qbit__pb2|g' generated/qbitwallet_pb2.py

sed -i 's|import qbitlegacy_pb2 as qbitlegacy__pb2|import qbitcoin.generated.qbitlegacy_pb2 as qbitlegacy__pb2|g' generated/qbitlegacy_pb2_grpc.py
sed -i 's|import qbitbase_pb2 as qbitbase__pb2|import qbitcoin.generated.qbitbase_pb2 as qbitbase__pb2|g' generated/qbitbase_pb2_grpc.py
sed -i 's|import qbitmining_pb2 as qbitmining__pb2|import qbitcoin.generated.qbitmining_pb2 as qbitmining__pb2|g' generated/qbitmining_pb2_grpc.py
sed -i 's|import qbitdebug_pb2 as qbitdebug__pb2|import qbitcoin.generated.qbitdebug_pb2 as qbitdebug__pb2|g' generated/qbitdebug_pb2_grpc.py
sed -i 's|import qbitstateinfo_pb2 as qbitstateinfo__pb2|import qbitcoin.generated.qbitstateinfo_pb2 as qbitstateinfo__pb2|g' generated/qbitstateinfo_pb2_grpc.py
sed -i 's|import qbitwallet_pb2 as qbitwallet__pb2|import qbitcoin.generated.qbitwallet_pb2 as qbitwallet__pb2|g' generated/qbitwallet_pb2_grpc.py
sed -i 's|import qbitdebug_pb2 as qbitdebug__pb2|import qbitcoin.generated.qbitdebug_pb2 as qbitdebug__pb2|g' generated/qbitdebug_pb2_grpc.py
sed -i 's|import qbitstateinfo_pb2 as qbitstateinfo__pb2|import qbitcoin.generated.qbitstateinfo_pb2 as qbitstateinfo__pb2|g' generated/qbitstateinfo_pb2_grpc.py
sed -i 's|import qbitwallet_pb2 as qbitwallet__pb2|import qbitcoin.generated.qbitwallet_pb2 as qbitwallet__pb2|g' generated/qbitwallet_pb2_grpc.py

find generated -name '*.py'|grep -v migrations|xargs autoflake --in-place

#docker run --rm \
#  -v $(pwd)/docs/proto:/out \
#  -v $(pwd)/qrl/protos:/protos \
#  pseudomuto/protoc-gen-doc --doc_opt=markdown,proto.md
#
#docker run --rm \
#  -v $(pwd)/docs/proto:/out \
#  -v $(pwd)/qrl/protos:/protos \
#  pseudomuto/protoc-gen-doc --doc_opt=html,index.html

popd > /dev/null
