export type UserType = 'internal_ops_manager' | 'client_transport_admin'

export interface UserScope {
  user_id: number
  email: string
  user_type: UserType
  access_scope: 'all_companies' | 'single_company'
  company_id: number | null
}

export interface AuthGateway {
  login(email: string, password: string): Promise<UserScope>
}
