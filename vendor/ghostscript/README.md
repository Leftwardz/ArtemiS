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

`Main.spec` copia `vendor/ghostscript/` inteiro para `dist/vendor/ghostscript/` ao lado de `Main.exe` (fora de `_internal/`, para evitar UPX quebrar os binários). Em runtime, `app/utils/ghostscript_paths.py` procura primeiro na pasta do executável.

Build recomendado: `.\scripts\build.ps1` (fetch GS se necessário, PyInstaller, verify_dist, smoke test).

## Deploy portátil (copiar para outro PC)

1. Copie a pasta **`dist/` inteira** (não só `Main.exe`). Obrigatório: `vendor/ghostscript/` com `bin/` e `lib/`.
2. Ajuste `config.json` (`database_location`, `search_folder`) — use `config.dist.json` na raiz do repo como modelo.
3. No PC destino, na pasta da instalação: `.\scripts\test_ghostscript_dist.ps1`
4. Se o motor Ghostscript aparecer indisponível: verifique antivírus, evite pasta de rede UNC, leia `logs/print.log` (diagnóstico no startup).
5. Configurações → Motor de impressão mostra status do Ghostscript empacotado.
