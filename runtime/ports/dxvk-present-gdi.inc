  // SPDX-License-Identifier: LGPL-2.1-or-later
  // Based on Neutron's PresentImageGdi: complete frame/latency accounting
  // without a Vulkan WSI surface owned by a different WebView process.
  HRESULT D3D11SwapChain::PresentImageGdi() {
    auto ctx = m_parent->GetContext();
    if (m_backBuffers.empty()) return E_FAIL;
    using Resolve = HWND (*)(HWND);
    static Resolve resolve = reinterpret_cast<Resolve>(::GetProcAddress(::GetModuleHandleA("dcomp.dll"), "pbi_dcomp_resolve_host"));
    m_gdiHost = resolve ? resolve(m_gdiWindow) : nullptr;
    if (!m_gdiHost) {
      if (m_backBuffers.size() > 1u) { RotateBackBuffers(ctx); ctx->FlushCsChunk(); }
      ++m_frameId;
      m_frameLatencySignal->signal(m_frameId);
      return S_OK;
    }
    D3D11_TEXTURE2D_DESC desc = {};
    m_backBuffers[0]->GetDesc(&desc);
    if (!m_gdiStaging) {
      desc.BindFlags = desc.MiscFlags = 0;
      desc.Usage = D3D11_USAGE_STAGING;
      desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
      HRESULT hr = m_parent->CreateTexture2D(&desc, nullptr, &m_gdiStaging);
      if (FAILED(hr)) return hr;
    }
    ctx->CopyResource(m_gdiStaging.ptr(), m_backBuffers[0].ptr());
    ctx->Flush();
    D3D11_MAPPED_SUBRESOURCE mapped = {};
    HRESULT hr;
    auto deadline = dxvk::high_resolution_clock::now() + std::chrono::milliseconds(200);
    do {
      hr = ctx->Map(m_gdiStaging.ptr(), 0, D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped);
      if (hr != DXGI_ERROR_WAS_STILL_DRAWING) break;
      ::Sleep(1);
    } while (dxvk::high_resolution_clock::now() < deadline);
    if (SUCCEEDED(hr)) {
      using Publish = BOOL (*)(HWND, HWND, const void*, UINT, UINT, UINT);
      static Publish publish = [] {
        HMODULE module = ::GetModuleHandleA("dcomp.dll");
        return module ? reinterpret_cast<Publish>(::GetProcAddress(module, "pbi_dcomp_publish")) : nullptr;
      }();
      m_gdiPixels.resize(size_t(desc.Width) * desc.Height * 4);
      for (UINT y = 0; y < desc.Height; ++y) {
        auto src = reinterpret_cast<const uint8_t*>(mapped.pData) + size_t(y) * mapped.RowPitch;
        auto dst = m_gdiPixels.data() + size_t(y) * desc.Width * 4;
        std::memcpy(dst, src, size_t(desc.Width) * 4);
        if (desc.Format == DXGI_FORMAT_R8G8B8A8_UNORM)
          for (UINT x = 0; x < desc.Width; ++x) std::swap(dst[x*4], dst[x*4+2]);
      }
      ctx->Unmap(m_gdiStaging.ptr(), 0);
      if (publish) publish(m_gdiHost, m_gdiWindow, m_gdiPixels.data(), desc.Width, desc.Height, desc.Width * 4);
    } else {
      Logger::warn(str::format("pbi-present: bounded readback failed hr=", hr));
    }
    if (m_backBuffers.size() > 1u) {
      RotateBackBuffers(ctx);
      ctx->FlushCsChunk();
    }
    ++m_frameId;
    m_frameLatencySignal->signal(m_frameId);
    return hr == DXGI_ERROR_WAS_STILL_DRAWING ? S_OK : hr;
  }
