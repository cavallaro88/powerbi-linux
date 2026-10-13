# Instalação no Fedora

Alvo inicial: **Fedora 44, x86_64 e Wayland nativo**. O projeto ainda está em desenvolvimento; login Microsoft não funciona. Refresh pela interface e save/reopen passaram em um modelo sintético de 158 tabelas, e o teste prolongado de duas horas também passou. A validação registra uma captura nativa discrepante em uma reabertura; sua causa ainda não foi estabelecida. Isso não garante compatibilidade com qualquer relatório empresarial.

Instale o RPM com `sudo dnf install ./powerbi-linux-0.1.0-2.noarch.rpm`. Ele instala a CLI e a integração com o desktop. O Power BI e os componentes Microsoft são instalados separadamente no seu usuário.

O perfil validado ocupa aproximadamente 9 GiB, além de runtime, downloads, cache derivado e relatórios. Em filesystems sem reflink, reparo/atualização precisam de espaço para outra cópia completa do perfil e seu cache; a anterior fica disponível para rollback.

Para preparar a instalação, use `pbi-linux setup` com o runtime e seu checksum e o instalador do Power BI 2.158.1177.0. O WebView2 fixo 154.0.4258.62 é baixado da Microsoft com checksum verificado. Para uso offline, forneça seu CAB com `--webview-runtime`. Consulte os argumentos e requisitos exatos no [guia de instalação](install.md). `--accept-license` confirma que você leu os termos e aceita a instalação e as alterações locais de compatibilidade.

Depois do setup, execute `pbi-linux open` ou abra PBIX/PBIP/PBIR com **Abrir com → Power BI Desktop (Wine)**. A opção `--make-default` no setup torna essa associação padrão. Prefixo, preferências e credenciais persistem; abrir um arquivo não recompila os patches.

Use `pbi-linux doctor --json` para diagnóstico. `repair` prepara uma cópia reparada; `update` troca o runtime explicitamente; `rollback` restaura a instalação anterior. `uninstall` preserva os dados. `uninstall --purge` remove os prefixos, runtime, cache derivado e configurações; os logs de diagnóstico são preservados.

A partir do RPM 0.1.0-2, o padrão é **sem limites de RAM/swap impostos pelo projeto, sem quota de CPU, heap automático do WebView2 e navegador sem as opções de economia**. `pbi-linux profile` mostra os ajustes; `pbi-linux profile unlimited` restaura o padrão. Os limites internos do navegador e os recursos da máquina continuam existindo.

Os ajustes são opcionais pela CLI: `pbi-linux profile --memory-max 8G --swap-max 2G --webview-heap 1024`, por exemplo. Também há `--cpu-quota`, `--renderer-process-limit` e `--browser-mode economy`. `normal` e `large` continuam como perfis econômicos explícitos, com 6G/2G ou 10G/4G e heap de 512 MiB. Feche todas as janelas e reabra para aplicar alterações; o comando preserva a sessão ativa. Veja [todos os ajustes e a migração](resources.md).

Se o seletor geral de fontes ficar bloqueado pelo login OneLake, importe um CSV local por **Relatório em branco → menu Obter dados → Texto/CSV**. Esse caminho passou sem login na instalação limpa. A desinstalação oculta a entrada do RPM para o seu usuário; `repair` restaura a integração, e o RPM pode ser removido separadamente pelo DNF.

Não envie relatórios empresariais, credenciais ou o prefixo inteiro em bugs. O projeto é independente da Microsoft e não tem suporte oficial dela.
