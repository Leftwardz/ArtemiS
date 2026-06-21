# Arquitetura de impressão (múltiplos backends)

Documento de referência da camada de impressão desacoplada e relatório
comparativo dos backends disponíveis.

## Visão geral

Toda impressão passa por uma **interface única** e por um **contrato de
parâmetros único**:

```
print_service.finish_print_job(...)
   └─ printer_handler.print_pdf_file(...)        # wrapper de compatibilidade
        └─ app.utils.printing.dispatch(job, backend_name)
             └─ <PrintBackend>.print_job(PrintJob) -> PrintResult
```

### Componentes (`app/utils/printing/`)

| Arquivo | Papel |
|---|---|
| `base.py` | `PrintJob` (parâmetros), `PrintResult`, `PrintBackend` (interface). |
| `registry.py` | Registra backends (import protegido), disponibilidade e `dispatch()` com logging. |
| `logger.py` | Log dedicado em `logs/print.log`. |
| `devmode.py` | DEVMODE por JOB, `DeviceCapabilities`, status do spooler. |
| `pdf_raster.py` | Rasteriza PDF→PNG via Ghostscript (para backends GDI). |
| `gdi_print.py` | Desenha páginas em um DC criado com o DEVMODE do job. |
| `backends/*.py` | Implementações concretas. |

### Contrato `PrintJob`

`pdf_path`, `printer`, `copies`, `duplex` (`simplex`/`long_edge`/`short_edge`),
`orientation` (`portrait`/`landscape`), `paper_size` (código **DMPAPER**, ex.
`9` = A4), `tray` (código DMBIN ou `None` = bandeja default), `slot_index`
(só PDFtoPrinter), `config`.

> **Defaults neutros**: hoje os chamadores passam `copies=1`, `simplex`,
> `portrait`, `tray=None`. Com isso, PDFtoPrinter e Ghostscript se comportam
> **exatamente** como antes da refatoração.

### Garantias

- **Sem alteração permanente da impressora**: nenhum backend usa `SetPrinter`.
  O DEVMODE é aplicado a um DC/handle temporário (vale só para o JOB) — não
  exige privilégio de administrador.
- **Resiliência**: um backend que não importe (dependência ausente) é apenas
  ignorado no `registry`; o app continua funcionando com os demais. Backends
  nunca levantam exceção — devolvem `PrintResult(ok=False, ...)`.
- **Sem fallback automático** (decisão do projeto): se o backend selecionado
  falhar, o erro é exibido na UI (comportamento atual preservado). Não há
  reimpressão em outro backend.

### Logging (`logs/print.log`)

Cada job registra: backend escolhido, todos os parâmetros, comando/DEVMODE
aplicado, capacidades da impressora (backend avançado), status do spooler e
sucesso/falha com detalhe do erro de driver/GS.

---

## Relatório comparativo

| Backend | Papel/job | Duplex | Cópias | Bandeja | Orientação | Admin? | Saída | Dependência | Maturidade |
|---|---|---|---|---|---|---|---|---|---|
| **PDFtoPrinter** | ❌ (usa preferência da impressora) | ❌ | ❌ | ❌ | ❌ | Não | Vetorial (driver) | `PDFtoPrinter*.exe` | Estável (produção) |
| **Ghostscript** | ✅ (`-sPAPERSIZE`) | ⚠️ best-effort | ✅ (`-dNumCopies`) | ❌ | ❌ | Não | Vetorial (mswinpr2) | Ghostscript empacotado | Estável |
| **Win32 DEVMODE** | ✅ (`dmPaperSize`) | ✅ (`dmDuplex`) | ✅ (`dmCopies`) | ✅ (`dmDefaultSource`) | ✅ (`dmOrientation`) | Não | **Rasterizada** (GDI) | Ghostscript (só p/ rasterizar) + pywin32 | Experimental |
| **Win32 avançada** | ✅ | ✅ | ✅ | ✅ | ✅ | Não | **Rasterizada** (GDI) | igual ao DEVMODE | Experimental |
| **XPS Print API** | ✅ (do PDF) | ⚠️ default do driver | ⚠️ default do driver | ⚠️ default do driver | ✅ (do PDF) | Não | Vetorial (XPS) | Ghostscript (`xpswrite`) + `XpsPrint.dll` | Experimental |

### PDFtoPrinter (produção)
- **Vantagens**: simples, rápido (handoff imediato ao spooler), saída vetorial fiel; paralelismo via 5 executáveis (`slot_index`).
- **Limitações**: não controla papel/duplex/cópias/bandeja por job — depende da preferência já configurada na impressora (por isso `validate_printer_paper` continua exigindo papel correto **apenas** neste backend).

### Ghostscript (produção)
- **Vantagens**: define o **papel por job** (`-sPAPERSIZE`); saída vetorial via `mswinpr2`; cópias por job; não precisa de admin.
- **Limitações**: bandeja não é controlada por job; duplex é *best-effort* (depende do device/driver); processo bloqueia até o GS terminar.

### Win32 DEVMODE por JOB (experimental)
- **Vantagens**: controle **completo** por job — papel, duplex, cópias, bandeja e orientação — montado em DEVMODE e validado por `DocumentProperties`, **sem admin** e **sem persistir** nada na impressora.
- **Limitações**: o `win32print`/GDI **não renderiza PDF**; por isso rasterizamos as páginas via Ghostscript (≈300 DPI) e desenhamos por GDI. Saída rasterizada (maior, e a nitidez depende do DPI). Logo, **ainda depende do Ghostscript** para rasterizar.

### Win32 Print API avançada (experimental)
- **Vantagens**: tudo do DEVMODE **mais** consulta de `DeviceCapabilities` (duplex/cópias/papéis/bandejas) com avisos quando o job pede algo não suportado, e leitura do **status do spooler** (`EnumJobs`) para diagnóstico no log.
- **Limitações**: mesmas do backend DEVMODE (saída rasterizada, dependência do Ghostscript p/ rasterizar).

### XPS Print API (experimental)
- **Vantagens**: pipeline 100% Windows moderno; submete XPS ao spooler via `StartXpsPrintJob`; saída vetorial; papel vem embutido do PDF→XPS.
- **Limitações**: opções de acabamento (duplex/bandeja/cópias) usam o **PrintTicket padrão** do driver nesta versão (não montamos PrintTicket customizado) — os parâmetros não aplicáveis são registrados em log. Depende de `XpsPrint.dll` e do Ghostscript (`-sDEVICE=xpswrite`). É o backend mais experimental.

---

## Como selecionar o backend

Configuração → **Motor de impressão** (combo lista apenas os backends
disponíveis na máquina). Persistido em `config.json` → `print_backend`.
Override opcional de DPI dos backends GDI: `config.json` → `win32_raster_dpi`
(default 300).

## Observações de design (escopo)

- A impressão continua ocorrendo na thread Tk (via `after`), como antes. Os
  backends rasterizados podem demorar mais; mover para worker thread fica como
  melhoria futura (fora do escopo desta entrega para não alterar o fluxo atual).
- Os parâmetros novos (cópias/duplex/bandeja) ainda não têm UI: usam defaults
  neutros. A infraestrutura já os transporta de ponta a ponta, prontos para
  uma futura tela de opções por produto/impressora.
