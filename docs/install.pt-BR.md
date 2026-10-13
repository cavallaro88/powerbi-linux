# Instalação no Fedora

Alvo inicial: **Fedora 44, x86_64 e Wayland nativo**. O projeto ainda está em desenvolvimento; login Microsoft pelo navegador e persistência após reabrir foram confirmados nesta máquina; o usuário confirmou uma publicação em homologação no Service; novos ciclos com a correção local pós-publicação e conectores autenticados continuam sujeitos a validação. Refresh pela interface e save/reopen passaram em um modelo sintético de 158 tabelas, e o teste prolongado de duas horas também passou. A validação registra uma captura nativa discrepante em uma reabertura; sua causa ainda não foi estabelecida. Isso não garante compatibilidade com qualquer relatório empresarial.

Instale o RPM com `sudo dnf install ./powerbi-linux-0.1.0-11.noarch.rpm`. Ele instala a CLI e a integração com o desktop. O Power BI e os componentes Microsoft são instalados separadamente no seu usuário.

Para atualizar a CLI, execute `sudo dnf upgrade ./powerbi-linux-0.1.0-11.noarch.rpm`
e `pbi-linux doctor`. Se o doctor indicar que os patches de diálogo estão
desatualizados, feche o Desktop, execute `pbi-linux repair` e confira novamente.
O repair aplica as correções de [credenciais](legacy-html.md) e do botão
[Continue no login](sign-in.md) em um novo perfil, preservando o anterior para
rollback. Ele não é necessário quando os patches já estão presentes e o doctor
passa. Atualizar apenas o RPM não modifica o prefixo existente. Cada usuário
precisa concluir sua autenticação interativa; login e persistência após reabrir
foram confirmados no host de validação.

Setup/repair do RPM 7 desativa os avisos de atualização do Desktop pela opção
oficial da Microsoft. A atualização só do RPM não muda essa preferência no
perfil existente. O notificador Fedora para versões validadas ainda é backlog;
o comando update atual troca o runtime. Veja a [política de atualização](updates.md).

O perfil validado ocupa aproximadamente 9 GiB, além de runtime, downloads, cache derivado e relatórios. Em filesystems sem reflink, reparo/atualização precisam de espaço para outra cópia completa do perfil e seu cache; a anterior fica disponível para rollback.

Para preparar a instalação, use `pbi-linux setup` com o runtime e seu checksum e o instalador do Power BI 2.158.1177.0. O WebView2 fixo 154.0.4258.62 é baixado da Microsoft com checksum verificado. Para uso offline, forneça seu CAB com `--webview-runtime`. Consulte os argumentos e requisitos exatos no [guia de instalação](install.md). `--accept-license` confirma que você leu os termos e aceita a instalação e as alterações locais de compatibilidade.

Depois do setup, execute `pbi-linux open` ou abra PBIX/PBIP/PBIR com **Abrir com → Power BI Desktop (Wine)**. A opção `--make-default` no setup torna essa associação padrão. Prefixo, preferências e credenciais persistem; abrir um arquivo não recompila os patches.

Use `pbi-linux doctor --json` para diagnóstico. `repair` prepara uma cópia reparada; `update` troca o runtime explicitamente; `rollback` restaura a instalação anterior. `uninstall` preserva os dados. `uninstall --purge` remove os prefixos, runtime, cache derivado e configurações; os logs de diagnóstico são preservados.

A partir do RPM 0.1.0-2, o padrão é **sem limites de RAM/swap impostos pelo projeto, sem quota de CPU, heap automático do WebView2 e navegador sem as opções de economia**. `pbi-linux profile` mostra os ajustes; `pbi-linux profile unlimited` restaura o padrão. Os limites internos do navegador e os recursos da máquina continuam existindo.

Os ajustes são opcionais pela CLI: `pbi-linux profile --memory-max 8G --swap-max 2G --webview-heap 1024`, por exemplo. Também há `--cpu-quota`, `--renderer-process-limit` e `--browser-mode economy`. `normal` e `large` continuam como perfis econômicos explícitos, com 6G/2G ou 10G/4G e heap de 512 MiB. Feche todas as janelas e reabra para aplicar alterações; o comando preserva a sessão ativa. Veja [todos os ajustes e a migração](resources.md).

Se o seletor geral de fontes ficar bloqueado pelo login OneLake, importe um CSV local por **Relatório em branco → menu Obter dados → Texto/CSV**. Esse caminho passou sem login na instalação limpa. A desinstalação oculta a entrada do RPM para o seu usuário; `repair` restaura a integração, e o RPM pode ser removido separadamente pelo DNF.

Não envie relatórios empresariais, credenciais ou o prefixo inteiro em bugs. O projeto é independente da Microsoft e não tem suporte oficial dela.

O setup/repair da receita RPM 6 habilita **Use my default web browser** para a
autenticação. Em perfis existentes, marque essa opção em **Arquivo → Opções e
configurações → Opções → Global → Segurança → Navegador de autenticação** e
reinicie o Desktop; não é necessário copiar o perfil por repair apenas para
mudar essa preferência. Veja o [diagnóstico do login](sign-in.md).

Conectores de banco são opcionais. Para MySQL, leia o [guia de conectores e
licenças](connectors.md), feche o Desktop e execute
`pbi-linux connector install mysql --accept-license`. Confira com
`pbi-linux connector status mysql` e `pbi-linux doctor`. O RPM 7 inclui essa CLI e
a correção da lista vazia. Instalar o RPM não instala o driver automaticamente;
um provedor externo existente não é sobrescrito.

A correção do menu Opções exige **runtime 0.1.2 e receita RPM 9**, aplicados ao
perfil além do upgrade da CLI. Veja [causa, instalação e validação](options-dialog.md).
Se a manutenção local já foi aplicada e o doctor passa, não repita update/repair.

O RPM 11 inclui a correção da [restauração do cache de dados](model-cache.md)
e utiliza o [logo original do Power BI](app-icon.md), extraído localmente do
executável já instalado. O logo aparece depois do provisionamento; não é
redistribuído no pacote. O doctor novo inclui a checagem `cache-restore`.
Perfis anteriores precisam aplicar a receita além do upgrade do RPM; nesta
máquina a manutenção local já foi aplicada e validada, sem outro repair.
