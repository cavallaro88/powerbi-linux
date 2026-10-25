# Power BI Linux — teste para Pop!_OS 24.04

**Pacote experimental para amd64/x86_64 e Wayland.** O runtime foi testado no
Fedora 44; a interface no COSMIC ainda precisa ser validada no Pop!_OS.
Use cópias dos seus projetos e mantenha backups completos.

## Atualizar uma instalação existente

Feche todas as janelas do Power BI. Instale o novo pacote e aplique as correções
à sua instalação por usuário:

```bash
sudo apt install ./powerbi-linux_0.1.0-16pop1_amd64.deb
pbi-linux repair
```

Esta atualização corrige o tamanho e a rolagem das configurações e impede a
seleção dos rótulos, preservando os campos editáveis. Não exige um novo runtime.
O reparo cria uma cópia de segurança gerenciada; reserve espaço para outra
instalação completa (aproximadamente 9 GiB).

## Primeira instalação

Extraia o bundle e abra um terminal nesta pasta. Instale o pacote:

```bash
sudo apt install ./powerbi-linux_0.1.0-16pop1_amd64.deb
```

Depois execute o setup **como seu usuário, sem sudo**:

```bash
./setup-popos.sh
```

O script usa o runtime que acompanha esta pasta. O setup verifica seu checksum,
mostra as versões e pede aceitação dos termos. Depois baixa o Power BI Desktop
**2.159.883.0** diretamente da Microsoft e prepara WebView2, .NET e os demais
componentes automaticamente. É necessário acesso à internet. Não precisa
instalar o Wine da distribuição nem selecionar WebView2 manualmente.

Se já tiver o EXE oficial exato, pode reaproveitá-lo:

```bash
./setup-popos.sh --installer '/caminho/para/PBIDesktopSetup_x64.exe'
```

Ao terminar, abra **Power BI Desktop (Wine)** no menu de aplicativos ou execute:

```bash
pbi-linux open
pbi-linux doctor
```

São necessários uma sessão Wayland, systemd de usuário e um driver Vulkan
funcional. Reserve aproximadamente 9 GiB para a instalação, além dos downloads,
runtime e relatórios; reparos podem precisar de outra cópia completa. Os testes
Fedora não certificam todas as janelas, diálogos ou GPUs no COSMIC.

O `pbi-linux setup` sem o script continua dependendo da futura release pública.
Este bundle fornece explicitamente o runtime local e não ativa downloads de
runtime não certificados. A Microsoft pode substituir a versão do EXE oferecida
em seu servidor: nesse caso, a verificação recusará o arquivo; não ignore o hash.

O `.deb` pode ser removido com `sudo apt remove powerbi-linux`; isso preserva sua
instalação por usuário. `pbi-linux uninstall` remove sua integração com o desktop
e preserva dados. `pbi-linux uninstall --purge` apaga os dados gerenciados.

`SHA256SUMS` permite conferir os arquivos com `sha256sum --check SHA256SUMS`.
O bundle de fontes contém o código do projeto e os fontes correspondentes do
Wine/DXVK. Nenhum instalador Microsoft ou perfil populado é distribuído aqui.
