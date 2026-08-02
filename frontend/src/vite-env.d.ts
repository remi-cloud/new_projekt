/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SINGULAR_SDK_KEY?: string
  readonly VITE_SINGULAR_SDK_SECRET?: string
  readonly VITE_SINGULAR_PRODUCT_ID?: string
  readonly VITE_SINGULAR_PRODUCT_NAME?: string
  readonly VITE_SINGULAR_PERSIST_DOMAIN?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
