# Release

## Antes de versionar

```bash
make check
python -m build
```

Confirme migrations, CHANGELOG, versão em `pyproject.toml` e `robia_ops.__version__`.

## Tag

```bash
git tag -a v3.0.0 -m "RobIA Ops v3.0.0"
git push origin v3.0.0
```

O workflow `release.yml` constrói wheel/sdist e cria a GitHub Release anexando os artefatos. Ele **não publica em PyPI** automaticamente.

## Versionamento

Use SemVer para a aplicação/toolkit. Alterações incompatíveis em API/schema exigem major ou plano de compatibilidade documentado.
