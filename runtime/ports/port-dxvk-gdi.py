#!/usr/bin/env python3
"""Scoped port of Neutron's GDI presentation design to DXVK 3.1.

Frames for WebView HWNDs go to their owner through dcomp. No Vulkan WSI
surface is created for those chains. GPU rendering remains enabled.
"""
from pathlib import Path
import subprocess
import difflib

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'dxvk-source'
changes = {}
def load(path):
    return subprocess.check_output(['git', '-C', str(SOURCE), 'show', 'HEAD:'+path], text=True)
def replace(s, old, new):
    assert s.count(old) == 1, old
    return s.replace(old, new, 1)
path = 'src/dxgi/dxgi_swapchain.cpp'
changes[path] = load(path)  # retire the pre-Present readback hook
path = 'src/dxgi/dxgi_surface.h'
changes[path] = replace(load(path), '  private:', '    HWND GetWindow() const { return m_window; }\n\n  private:')
path = 'src/d3d11/d3d11_swapchain.h'
s = load(path)
s = replace(s, '    bool                      m_hasHud = false;', '''    HWND                      m_gdiWindow = nullptr;
    HWND                      m_gdiHost = nullptr;
    Com<ID3D11Texture2D>       m_gdiStaging;
    std::vector<uint8_t>      m_gdiPixels;
    HRESULT PresentImageGdi();

    bool                      m_hasHud = false;''')
changes[path] = s
path = 'src/d3d11/d3d11_swapchain.cpp'
s = load(path)
s = replace(s, '#include "../util/util_win32_compat.h"', '#include "../util/util_win32_compat.h"\n#include "../dxgi/dxgi_surface.h"')
s = replace(s, '    CreateFrameLatencyEvent();', '''    if (env::getEnvVar("PBI_COMPOSITION") == "1") {
      using Resolve = HWND (*)(HWND);
      static Resolve resolve = [] {
        HMODULE module = ::LoadLibraryA("dcomp.dll");
        return module ? reinterpret_cast<Resolve>(::GetProcAddress(module, "pbi_dcomp_resolve_host")) : nullptr;
      }();
      HWND window = static_cast<DxgiSurfaceFactory*>(m_surfaceFactory.ptr())->GetWindow();
      WCHAR cls[128] = {};
      ::GetClassNameW(window, cls, 128);
      // Chromium creates some windows before attaching the owner ancestor.
      // Select the presentation mode now; resolve the recipient at Present.
      if (resolve && !std::wcsncmp(cls, L"Chrome_", 7)
       && (m_desc.SwapEffect == DXGI_SWAP_EFFECT_DISCARD || m_desc.SwapEffect == DXGI_SWAP_EFFECT_SEQUENTIAL)
       && (m_desc.Format == DXGI_FORMAT_B8G8R8A8_UNORM || m_desc.Format == DXGI_FORMAT_R8G8B8A8_UNORM)) {
        m_gdiWindow = window;
        m_gdiHost = resolve(window);
      }
      Logger::warn(str::format("pbi-present: hwnd=", (void*)window, " host=", (void*)m_gdiHost,
        " gdi=", bool(m_gdiWindow), " effect=", m_desc.SwapEffect, " format=", m_desc.Format, " size=", m_desc.Width, "x", m_desc.Height));
    }
    CreateFrameLatencyEvent();''')
s = replace(s, '    m_presenter->destroyResources();', '    if (m_presenter) m_presenter->destroyResources();')
s = replace(s, '    if (m_desc.Format != pDesc->Format)', '    if (m_presenter && m_desc.Format != pDesc->Format)')
s = replace(s, '    if (m_desc.Width != pDesc->Width || m_desc.Height != pDesc->Height)', '    if (m_presenter && (m_desc.Width != pDesc->Width || m_desc.Height != pDesc->Height))')
s = replace(s, '    m_desc = *pDesc;\n    CreateBackBuffers();', '    m_desc = *pDesc;\n    m_gdiStaging = nullptr;\n    CreateBackBuffers();')
s = replace(s, '      VkResult status = m_presenter->checkSwapChainStatus();', '      if (m_gdiWindow) return S_OK;\n      VkResult status = m_presenter->checkSwapChainStatus();')
s = replace(s, '    if (m_presenter->supportsColorSpace(vkColorSpace))', '''    if (m_gdiWindow) return vkColorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR
      ? DXGI_SWAP_CHAIN_COLOR_SPACE_SUPPORT_FLAG_PRESENT : 0;
    if (m_presenter->supportsColorSpace(vkColorSpace))''')
s = replace(s, '    if (!m_presenter->supportsColorSpace(colorSpace))', '''    if (m_gdiWindow) return colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR ? S_OK : E_INVALIDARG;
    if (!m_presenter->supportsColorSpace(colorSpace))''')
s = replace(s, '    if (pMetaData->Type == DXGI_HDR_METADATA_TYPE_HDR10)', '    if (m_presenter && pMetaData->Type == DXGI_HDR_METADATA_TYPE_HDR10)')
s = replace(s, '    m_presenter->setSyncInterval(SyncInterval);', '    if (m_gdiWindow) return PresentImageGdi();\n\n    m_presenter->setSyncInterval(SyncInterval);')
s = replace(s, '  void D3D11SwapChain::CreatePresenter() {', '  void D3D11SwapChain::CreatePresenter() {\n    if (m_gdiWindow) return;')
s = replace(s, '  void D3D11SwapChain::DestroyLatencyTracker() {', '  void D3D11SwapChain::DestroyLatencyTracker() {\n    if (!m_latency) return;')
body = (ROOT / 'dxvk-present-gdi.inc').read_text()
s = replace(s, '  void D3D11SwapChain::RotateBackBuffers(', body + '\n\n  void D3D11SwapChain::RotateBackBuffers(')
changes[path] = s
patch = ''
for path, changed in changes.items():
    (SOURCE / path).write_text(changed)
    patch += ''.join(difflib.unified_diff(load(path).splitlines(True), changed.splitlines(True), fromfile='a/'+path, tofile='b/'+path))
(ROOT / 'dxvk-3.1-composition.patch').write_text(patch)
