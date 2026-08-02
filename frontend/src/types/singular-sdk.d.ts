declare module 'singular-sdk' {
  export interface SingularInitParams {
    singularDeviceId: string
  }

  export class SingularConfig {
    constructor(sdkKey: string, sdkSecret: string, productId: string)
    withCustomUserId(userId: string): SingularConfig
    withAutoPersistentSingularDeviceId(domain: string): SingularConfig
    withLogLevel(level: number): SingularConfig
    withSessionTimeoutInMinutes(timeout: number): SingularConfig
    withProductName(productName: string): SingularConfig
    withPersistentSingularDeviceId(singularDeviceId: string): SingularConfig
    withInitFinishedCallback(
      callback: (params: SingularInitParams) => void,
    ): SingularConfig
  }

  export const singularSdk: {
    init(config: SingularConfig): void
    pageVisit(): void
    event(eventName: string, attributes?: Record<string, unknown>): void
    conversionEvent(eventName: string, attributes?: Record<string, unknown>): void
    revenue(
      eventName: string,
      currency: string,
      amount: number,
      attributes?: Record<string, unknown>,
    ): void
    login(customUserId: string): void
    logout(): void
    getSingularDeviceId(): string | null
  }
}
