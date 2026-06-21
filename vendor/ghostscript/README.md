# Ghostscript empacotado (Windows 64-bit)

O ArtemiS usa o Ghostscript como motor de impressão opcional (`print_backend: ghostscript` no `config.json`).

## Estrutura esperada

```
vendor/ghostscript/
├── VERSION              # versão fixa (ex.: 10.04.0)
├── LICENSE.txt          # licença AGPL (copiada pelo script de download)
├── README.md
├── bin/
│   ├── gswin64c.exe     # console — usado pelo ArtemiS
│   └── gsdll64.dll
└── lib/                 # recursos obrigatórios (fontes, init, etc.)
```

Sem `bin/` e `lib/`, a impressão via Ghostscript não funciona.

## Obter os binários (após clonar o repositório)

Na raiz do projeto, no PowerShell:

```powershell
.\scripts\fetch_ghostscript.ps1
```

O script baixa o instalador oficial (`gs10040w64.exe` para a versão em `VERSION`), instala em pasta temporária e copia `bin/` + `lib/` para cá.

## Duas formas de versionar no Git

### A — Repositório leve (padrão deste projeto)

- `bin/` e `lib/` estão no `.gitignore`
- Cada desenvolvedor ou CI roda `fetch_ghostscript.ps1` uma vez
- `VERSION` + script garantem a mesma versão em todo lugar

### B — Clone já pronto (sem script)

1. Rode `fetch_ghostscript.ps1` uma vez
2. Remova ou esvazie `vendor/ghostscript/.gitignore`
3. Faça commit de `bin/`, `lib/` e `LICENSE.txt` (~30–45 MB)

Útil quando a equipe não pode baixar na rede corporativa.

### C — Git LFS (opcional)

Para não inflar o histórico do Git com binários, use LFS nos arquivos de `vendor/ghostscript/bin/` e `lib/`.

## Licença

Ghostscript é distribuído sob **AGPL**. O arquivo `LICENSE.txt` deve acompanhar o projeto e o instalador. Revise com jurídico se o ArtemiS for distribuído como produto fechado.

## PyInstaller

`Main.spec` inclui `vendor/ghostscript/bin` e `lib` no pacote. Em runtime, `app/utils/ghostscript_paths.py` resolve o caminho do executável (desenvolvimento e `.exe`).
