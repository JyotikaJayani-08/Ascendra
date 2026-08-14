export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = 'An error occurred';
    try {
      const errorData = await response.json();
      if (Array.isArray(errorData.detail)) {
        errorMessage = errorData.detail.map((e: any) => `${e.loc[e.loc.length - 1]}: ${e.msg}`).join(', ');
      } else {
        errorMessage = errorData.detail || errorData.message || errorMessage;
      }
    } catch (e) {
      errorMessage = response.statusText;
    }
    throw new Error(errorMessage);
  }

  // 204 No Content has no body — don't try to parse JSON
  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export async function fetchApiFormData(endpoint: string, formData: FormData, options: RequestInit = {}) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  
  const headers = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    method: options.method || 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    let errorMessage = 'An error occurred';
    try {
      const errorData = await response.json();
      if (Array.isArray(errorData.detail)) {
        errorMessage = errorData.detail.map((e: any) => `${e.loc[e.loc.length - 1]}: ${e.msg}`).join(', ');
      } else {
        errorMessage = errorData.detail || errorData.message || errorMessage;
      }
    } catch (e) {
      errorMessage = response.statusText;
    }
    throw new Error(errorMessage);
  }

  // 204 No Content has no body — don't try to parse JSON
  if (response.status === 204) {
    return null;
  }

  return response.json();
}
