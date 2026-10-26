# Primeiro preflight multi-distribuição

Execução iniciada em **2026-10-25 23:40:26 UTC**. Esta é a primeira parte da
[etapa A do plano](multi-distro-plan.md), não a conclusão da etapa nem certificação
de suporte. Nenhuma allowlist, receita de runtime ou pacote de produção mudou.

## Ambiente e isolamento

Host verificado: Intel i5-1135G7, 8 CPUs lógicas, aproximadamente 15 GiB de RAM
visíveis e 9,5 GiB disponíveis no início. KVM acessível ao usuário; Podman,
QEMU, libvirt e virt-install disponíveis. Não havia VMs na conexão libvirt de
usuário. Disco livre: aproximadamente 43 GiB antes e 40 GiB após os ensaios.

Foram usados containers Podman rootless, sequenciais, com limite de 2 CPUs,
3 GiB de RAM e 512 processos. Somente cópias selecionadas de fontes públicas,
o arquivo de runtime verificado e diretórios de resultados foram montados.
Não foram expostos home, sockets do desktop, dispositivos gráficos, credenciais,
relatórios ou prefixo ativo. Containers foram removidos ao sair; imagens-base e
evidências permanecem em disco. Não há ambiente desktop de testes em execução.

## Entradas e resultado

Runtime local **0.1.5**, conferido contra `packaging/setup.json`:

`291bb52fca8c27f2446ec4a05aaf982bb43d8c13e6b3787f32a1328ad890f05a`

| Alvo | Python | glibc | Testes unitários | Documentação | Auditoria ELF após instalar provedores |
|---|---|---|---|---|---|
| Ubuntu 24.04 | 3.12.3 | 2.39 | 156 aprovados | Aprovada | Nenhuma dependência ELF não resolvida |
| Debian 13 | 3.13.5 | 2.41 | 156 aprovados | Aprovada | Nenhuma dependência ELF não resolvida |
| Arch, inventário desta execução | 3.14.8 | 2.44 | 156 aprovados | Aprovada | `wpcap.so` requer `libpcap.so.0.8`, ausente |

Nos três alvos, `wine --version` retornou `wine-11.18` com exit code zero sem
criar prefixo. Isso comprova somente execução desse comando, não Wine/WoW64
funcional, inicialização gráfica ou instalação do Power BI.

Foram inspecionados 40 arquivos ELF por alvo. A maior versão GLIBC observada nos
registros de versão desses arquivos foi 2.38; isso não basta para declarar um
baseline glibc menor que o do builder, pois dependências e carregamentos dinâmicos
exigem análise própria. Não houve erro de versão de símbolo nas saídas `ldd`.
As bibliotecas carregadas pelo `doctor` e as ferramentas systemd-run, ntlm_auth,
cabextract, Zenity e xdg-open estavam presentes no primeiro ensaio.

A aprovação dos testes de plataforma preserva intencionalmente a rejeição das
novas distribuições no produto atual. Esses testes não são evidência de que o
launcher já permite executar nelas.

### Identidade das imagens-base

As tags foram resolvidas nesta execução; os comandos de teste usaram os IDs
imutáveis locais. Os inventários de pacotes foram guardados separadamente:
instalar pacotes de repositórios ativos não torna o filesystem resultante
reproduzível apenas pelo digest da imagem-base.

| Alvo | ID da imagem-base |
|---|---|
| Ubuntu | `6277ab668b2ad3c3ab851d370faa1690d324b30db29d342527f61fed28f20f36` |
| Debian | `133aec7ab1411181567fef7fc3f4512123e1f9660090b49851de4b698b4ff772` |
| Arch | `c22c3194d74cdee63a036f904175005556c8b5c3044ed268e059438e2bc60bfd` |

## Achados acionáveis

1. **Não basta traduzir as dependências do RPM.** No Ubuntu/Debian, a auditoria
   exigiu incluir explicitamente `libxkbregistry0`, `libwayland-egl1`,
   `libasound2t64`, `libpcap0.8t64`, `libgstreamer1.0-0` e
   `libgstreamer-plugins-base1.0-0` no conjunto de provedores do segundo ensaio.
   Eles resolvem os imports ELF; ainda não definem a lista final de dependências
   obrigatórias do produto. Decidir separadamente o que pode ser opcional.
2. **Arch tem diferença real de SONAME.** Mesmo com `libpcap 1.11.0-1`
   instalado, `wpcap.so` do runtime exige `libpcap.so.0.8`, que não foi resolvida.
   Não criar symlink artificial. Determinar se captura de pacotes pertence ao
   escopo do Power BI; se não pertencer, registrar explicitamente a limitação;
   se for necessária, corrigir o build/carregamento de forma portável e testar
   também Fedora. Não declarar o runtime inteiro incompatível apenas por esse
   módulo, nem ignorar a falta sem decisão documentada.
3. **A busca de bibliotecas Wine precisa ser considerada.** O `ldd` inicial
   executado isoladamente nos módulos reportava `ntdll.so`/`win32u.so` ausentes.
   A segunda auditoria usou `LD_LIBRARY_PATH=/runtime/lib/wine/x86_64-unix`,
   resolvendo esses arquivos a partir do próprio runtime. Não são pacotes de
   sistema faltantes e isso não altera a configuração do launcher.
4. **Containers não cobrem a sessão.** Ter `systemd-run` e a biblioteca Vulkan
   instalados não comprova sessão systemd de usuário ou GPU/Vulkan funcional.

## Próximos gates

- Consolidar provedores por distribuição, incluindo bibliotecas carregadas com
  `dlopen`, e decidir o tratamento do módulo de captura no Arch.
- Provisionar uma VM Ubuntu primeiro, sem iniciar VMs em paralelo. Como ponto
  de partida: 4 vCPUs, 6 GiB de RAM e disco qcow2 expansível; conferir novamente
  memória/disco antes de escolher capacidade e baixar a imagem.
- Validar Vulkan na VM antes de executar instaladores Microsoft. Se a GPU virtual
  não satisfizer o runtime, usar o ambiente para testes de sistema e providenciar
  outro ambiente gráfico para certificação, sem desabilitar verificações.
- Executar os probes Wayland/WoW64 e somente depois o setup autorizado no ambiente
  descartável. Pacotes DEB/Arch e alterações na aceitação de plataforma continuam
  pendentes, assim como todos os gates gráficos e de release.

## Evidências locais

Diretório da execução: `.local/multi-distro/20261025T234026Z/`.

- `summary.json`: primeiro ensaio de testes; seu status `passed` refere-se aos
  testes unitários/documentação, não à resolução integral de dependências.
- `<alvo>/probe.json`: os-release, ferramentas, pacotes, testes e readelf/ldd
  iniciais, com saídas completas.
- `<alvo>/abi.json`: auditoria complementar final e `wine --version`.
- `<alvo>/image.json`, `pull.log`, `run.log` e `abi-run.log`: identidade e logs.
- Harnesses: `.local/multi-distro/run.py` e `check-abi.py`.

Um bundle de evidências acompanha esta entrega, sem runtime binário ou prefixos.
Os harnesses são experimentais e não fazem parte da CLI ou CI de produção.
