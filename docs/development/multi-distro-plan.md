# Plano de suporte a Arch Linux, Debian e Ubuntu

**Status: proposta; não habilita novas distribuições.** O alvo atual continua
sendo Fedora 44 x86_64 com Wayland. As versões abaixo são candidatas a validação,
não declarações de compatibilidade. Nenhuma instalação do usuário será alterada
para executar este plano.

## 1. Escopo e decisões propostas

- Preservar o RPM e a experiência existente no Fedora como baseline de regressão.
- Adicionar Ubuntu 24.04 LTS, Debian 13 e Arch Linux x86_64, inicialmente em
  Wayland, com Vulkan funcional e sessão de usuário systemd.
- Para Arch, registrar data do snapshot, versões dos pacotes e compositor:
  “Arch atualizado” não é uma identificação reproduzível do ambiente.
- Validar GNOME primeiro em cada alvo; promover KDE separadamente quando houver
  evidência. Uma aprovação em um compositor não certifica todos os outros.
- Tratar outras versões de Ubuntu/Debian, distribuições derivadas, X11, ARM,
  Flatpak e AppImage como fora desta primeira entrega. Pop!_OS e Mint não herdam
  suporte por `ID_LIKE`.
- Reutilizar o runtime versionado atual se ele passar na auditoria de ABI e nos
  testes nativos. Só criar outro runtime se uma incompatibilidade demonstrada
  exigir isso; não substituir pelo Wine da distribuição.
- Distribuir inicialmente artefatos nas releases do projeto: RPM, DEB e receita
  Arch com pacote resultante. Repositórios APT/pacman e publicação no AUR ficam
  para uma etapa posterior, após estabilização e definição de assinatura.

A ordem recomendada é **Ubuntu → Debian → Arch**. A imagem de build já usa
Ubuntu 24.04, o que facilita investigação, mas não comprova execução no Ubuntu.
Debian reaproveita o trabalho DEB sem presumir igualdade de dependências; Arch
adiciona empacotamento próprio e risco de atualizações rolling.

## 2. Diagnóstico do código atual

| Área | Evidência no repositório | Consequência |
|---|---|---|
| Aceitação de distribuição | `src/pbi_linux/platforms.py`: `status()` só aceita `ID=fedora`; `TARGETS` e `ntlm_help()` são específicos do Fedora | Modelar alvos explicitamente; não liberar por ancestralidade |
| Testes de plataforma | `tests/unit/test_platforms.py` rejeita Ubuntu e derivados | Alterar apenas junto com os novos estados e seus testes |
| Empacotamento | `packaging/powerbi-linux.spec`, `tools/build-rpm.py` | Falta caminho atual para DEB e Arch |
| Histórico DEB | Commit `47a5fec` removeu builder, metadados Debian e bundle Pop!_OS | Consultar o histórico como referência, sem restaurá-lo como suporte comprovado |
| ABI do runtime | `runtime/Dockerfile`: Ubuntu 24.04 fixado por digest; comentário declara glibc 2.39 | Auditar símbolos ELF e bibliotecas realmente usadas em cada alvo |
| Python | RPM e guia de build exigem Python >= 3.12 | Confirmar disponibilidade no alvo; não reduzir requisito sem verificar código e testes |
| Sessão e bibliotecas | `src/pbi_linux/launch.py`, `cli.py` e `common.py`: systemd de usuário, `ntlm_auth`, Vulkan e `libodbc.so.2` | Mapear provedores por distribuição e verificar capacidade real no doctor |
| CI | `.github/workflows/checks.yml`: verificações em container Fedora 44 | Adicionar matriz de testes e pacotes; manter QA gráfica separada |
| Evidência de release | `docs/release-evidence.example.json` contém `fedora_version` | Generalizar identidade do host antes de certificar outros alvos |

## 3. Etapas executáveis e critérios de saída

### Etapa A — Inventário e prova de compatibilidade do runtime

1. Provisionar VMs descartáveis com desktop para cada alvo e ambientes limpos de
   container para checagens de pacote. Não usar o prefixo ou contas ativos.
2. Registrar `/etc/os-release`, arquitetura, Python, glibc, systemd, kernel,
   compositor, sessão, GPU/driver Vulkan e inventário de pacotes. Fixar imagens
   de CI por digest e guardar a identidade da VM/snapshot.
3. Inspecionar os ELF do arquivo de runtime exato: interpretador, `NEEDED`,
   símbolos GLIBC/GLIBCXX e dependências carregadas dinamicamente. Separar
   bibliotecas fornecidas pelo runtime das exigidas ao host.
4. Resolver dependências pelos repositórios de cada alvo. O ponto de partida é
   a lista do RPM, não uma lista inventada por equivalência de nomes. Verificar
   especialmente o provedor de `ntlm_auth`, unixODBC, PulseAudio/compatibilidade,
   Wayland, EGL, Vulkan, fontes, cabextract, Zenity e ferramentas XDG.
5. Executar probes mínimos de Wine/WoW64, Wayland e Vulkan no ambiente gráfico.
   Confirmar se o runtime atual dispensa bibliotecas de host de 32 bits; não
   habilitar multiarch/multilib sem necessidade demonstrada.

**Saída:** relatório por alvo com dependências resolvidas, checksum do runtime,
probes e bloqueios. Se houver incompatibilidade de ABI, decidir entre excluir
explicitamente a versão, reconstruir sobre baseline adequado ou manter variante
justificada. Não copiar bibliotecas de sistema arbitrariamente para contorná-la.

### Etapa B — Contrato de plataforma e diagnóstico

1. Separar “alvo reconhecido”, “experimental”, “validado” e “não suportado”, sem
   confundir reconhecimento da distro com aprovação do ambiente gráfico.
2. Usar allowlist de `ID` e versão; Arch exige identificação do snapshot nos
   resultados. Não aceitar automaticamente `ID_LIKE`.
3. Generalizar `ntlm_help()`, mensagens do onboarding e `doctor`, mantendo dicas
   específicas de instalação por alvo e erros para recursos ausentes.
4. Cobrir parsing, versões aceitas/rejeitadas, derivados, versões futuras,
   dependências ausentes e preservação do comportamento Fedora com testes.
5. Definir como os testes experimentais serão executados sem abrir a allowlist
   pública prematuramente. Se houver mecanismo interno, ele deve ser explícito,
   avisar sobre ausência de suporte e nunca contornar SHA, ABI ou integridade.

**Saída:** testes unitários passando nos alvos e diagnóstico acionável, com
status experimental claramente separado da promoção pública de suporte.

### Etapa C — Empacotamento sem duplicar o produto

1. Definir uma instalação/staging comum para CLI, módulos, helpers, receitas,
   licenças e integração desktop. Os formatos nativos fornecem dependências e
   metadados próprios; não devem ganhar implementações divergentes do setup.
2. Criar DEB com metadados, dependências, copyright e tratamento idempotente dos
   caches desktop/MIME. Construir e instalar separadamente em Ubuntu e Debian;
   compartilhar um binário DEB só se a mesma saída passar em ambos.
3. Criar `PKGBUILD` com fontes de release imutáveis e SHA-256; gerar `.SRCINFO`
   para eventual publicação no AUR. Construir em chroot limpo e testar pacote
   resultante. Separar arquitetura da CLI da arquitetura do runtime utilizado.
4. Manter instaladores Microsoft, runtime baixado e prefixos fora do pacote,
   como no contrato atual. Hooks não executam Wine, setup, downloads ou acesso
   a credenciais; apenas integração de sistema necessária.
5. Testar instalação, atualização, reinstalação, remoção e, no DEB, purge.
   Preservar dados XDG do usuário em todas essas operações. Validar dependências,
   permissões, launcher, ícone, MIME e abertura de arquivos com espaços.
6. Rodar verificadores nativos (Lintian/namcap ou equivalentes disponíveis),
   registrar avisos e justificar exceções. Revalidar o RPM após o staging comum.

**Saída:** pacotes instaláveis em ambientes limpos, sem dependências ocultas e
com testes de ciclo de vida aprovados. Construção de pacote não certifica GUI.

### Etapa D — CI e evidências por alvo

1. Expandir a CI para Fedora 44, Ubuntu 24.04, Debian 13 e snapshot Arch fixado:
   testes unitários, documentação, metadados desktop/MIME, build e ciclo de vida
   de pacotes em jobs apropriados para cada distribuição.
2. Containers cobrem código e pacotes; VMs/sessões gráficas reais cobrem
   systemd de usuário, compositor, Vulkan e Power BI. Não apresentar execução
   headless em container como validação desktop.
3. Evoluir o schema de evidência e `tools/release-check.py` com testes e
   compatibilidade explícita para registros antigos: distribuição/versão,
   snapshot, compositor, GPU/driver, arquitetura, pacote/checksum, runtime/SHA,
   Power BI, WebView2 e casos de teste. Não reclassificar evidência Fedora como
   evidência genérica de Linux.
4. Vincular cada resultado ao pacote e runtime exatos. Reutilizar resultados
   entre alvos apenas quando o caso for comprovadamente independente do host;
   nunca reutilizar aprovação gráfica de outra distro.

**Saída:** falhas bloqueiam apenas a promoção do alvo afetado, sem encobrir
regressões compartilhadas; evidências permanecem disponíveis como artefatos.

### Etapa E — QA nativa e promoção gradual

Executar por combinação de distribuição e compositor pretendida:

- Instalação limpa, download verificado e setup interrompido/retomado.
- `doctor`, inicialização pelo menu e CLI, diagnósticos de dependências ausentes.
- PBIX, caminhos relativos PBIP/PBIR, importação CSV e criação de visual.
- Salvar, fechar e reabrir com verificação independente dos dados sintéticos.
- Janelas, redimensionamento, menus, modais, tooltips, seletores, escala e tema.
- Testes locais de conectores; conectividade real, login e publicação apenas em
  ambiente de teste autorizado, com evidência e limites de suporte explícitos.
- Atualização e repair no próprio prefixo, falha/retomada, remoção/associações e sessão prolongada de duas
  horas, conforme a matriz de release existente.
- Regressão Fedora com o mesmo candidato quando houver mudanças compartilhadas.

**Saída:** todos os gates aplicáveis aprovados, limitações documentadas e
artefatos exatos identificados. Só então promover o alvo e atualizar allowlist,
README, instalação, troubleshooting, known issues e notas de release. Recursos
não aprovados não podem desaparecer da matriz para obter aprovação artificial.

## 4. Pacotes de trabalho sugeridos

| ID local | Entrega | Depende de | Aceitação |
|---|---|---|---|
| M1 | Inventário ABI e dependências dos alvos | — | Relatórios e probes isolados por alvo |
| M2 | Contrato de plataforma e doctor | M1 | Testes de estados/versões; Fedora preservado |
| M3 | Staging comum e DEB Ubuntu | M1, M2 | Build limpo e ciclo de vida; RPM sem regressão |
| M4 | Validação e ajustes Debian | M3 | Dependências e pacote testados no Debian |
| M5 | PKGBUILD e pacote Arch | M1, M2, staging de M3 | Build em chroot, checksum e ciclo de vida |
| M6 | CI e schema de evidências | M2; integrar M3–M5 quando disponíveis | Matriz bloqueante e testes do release-check |
| M7 | QA e release Ubuntu | M3, M6 | Gates nativos e documentação do alvo |
| M8 | QA e release Debian | M4, M6 | Gates nativos e documentação do alvo |
| M9 | QA e release Arch | M5, M6 | Gates nativos; snapshot registrado |

Estes IDs organizam a proposta; não representam tarefas já criadas no Kanban.
Não estimar prazo de entrega antes de M1: ABI, autenticação e comportamento dos
compositores podem mudar substancialmente o esforço.

## 5. Restrições de segurança e manutenção

- Preservar verificações SHA, recibos/proveniência de build, retomada do setup e
  ordem de instalação do .NET. Mudanças nesses contratos exigem validação própria.
- Conforme decisão posterior, manutenção é in-place, sem snapshots ou rollback;
  falhas devem ficar explícitas e permitir nova tentativa, sem copiar o prefixo.
- Isolar XDG_DATA_HOME, XDG_CONFIG_HOME, XDG_CACHE_HOME e XDG_STATE_HOME em testes;
  não ler relatórios, contas ou credenciais reais para validar empacotamento.
- Instalações Microsoft e testes autenticados exigem autorização específica;
  preparar os pacotes não constitui autorização para executá-los no host.
- Não publicar pacotes, abrir repositórios ou alterar releases existentes durante
  o planejamento. Manter fontes correspondentes e licenças junto aos runtimes.
- Definir manutenção de Arch com rechecagens periódicas e em atualização de
  runtime/dependências críticas; uma aprovação pontual não cobre snapshots futuros.

## 6. Próxima decisão

Aprovar a matriz inicial e disponibilizar ambientes gráficos descartáveis para
Ubuntu 24.04, Debian 13 e Arch. A primeira implementação deve ser M1, antes de
restaurar o caminho DEB ou liberar novas distribuições no launcher.
