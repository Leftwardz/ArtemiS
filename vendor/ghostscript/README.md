# Ghostscript empacotado (Windows 64-bit)

O ArtemiS usa o Ghostscript como motor de impressão (`print_backend: ghostscript` no `config.json`) e para rasterizar PDF nos backends Win32/XPS.

## Estrutura (versionada no Git)

```
vendor/ghostscript/
├── VERSION              # versão fixa (ex.: 10.04.0)
├── LICENSE.txt          # licença AGPL
├── README.md
├── bin/
│   ├── gswin64c.exe     # console — usado pelo ArtemiS
│   └── gsdll64.dll
└── lib/                 # recursos obrigatórios (fontes, init, etc.)
```

Após `git clone`, os binários já vêm no repositório — **não é necessário** rodar script de download nem instalar Ghostscript no sistema.

## Atualizar a versão (mantenedores)

Se precisar subir a versão do Ghostscript:

```powershell
# Edite vendor/ghostscript/VERSION, depois:
.\scripts\fetch_ghostscript.ps1
git add vendor/ghostscript/
```

## Licença

Ghostscript é distribuído sob **AGPL**. O arquivo `LICENSE.txt` deve acompanhar o projeto e o instalador. Revise com jurídico se o ArtemiS for distribuído como produto fechado.

## PyInstaller

`Main.spec` inclui `vendor/ghostscript/bin` e `lib` no pacote one-file. Em runtime, `app/utils/ghostscript_paths.py` resolve o caminho do executável via `sys._MEIPASS` (`.exe`) ou `vendor/` (desenvolvimento).
