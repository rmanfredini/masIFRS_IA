import h5py

path = "caminho/arquivo.he5"
with h5py.File(path, "r") as f:
    def show(name, obj):
        print(name, type(obj))
    f.visititems(show)

    # Exemplo de caminhos comuns (ajuste GridName/Variavel):
    dset = f["/HDFEOS/GRIDS/<GridName>/Data Fields/<Variavel>"]
    data = dset[...]              # numpy array
    print(dset.shape, dset.dtype)
    print(dict(dset.attrs))       # atributos do dataset

    # Metadados EOS (texto com info de projeção/grade):
    meta = f["/HDFEOS/ADDITIONAL/FILE_ATTRIBUTES/StructMetadata.0"][()]
    print(meta.decode() if isinstance(meta, bytes) else meta)