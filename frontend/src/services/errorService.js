export function normalizeApiError(error, fallbackMessage = 'Request failed.') {
  if (error?.name === 'AbortError') {
    return 'Request cancelled.';
  }

  const responseData = error?.response?.data;

  if (typeof responseData === 'string' && responseData.trim()) {
    return responseData;
  }

  if (responseData && typeof responseData === 'object') {
    if (typeof responseData.detail === 'string' && responseData.detail.trim()) {
      return responseData.detail;
    }

    if (typeof responseData.error === 'string' && responseData.error.trim()) {
      return responseData.error;
    }

    for (const value of Object.values(responseData)) {
      if (Array.isArray(value) && value.length && typeof value[0] === 'string') {
        return value[0];
      }
    }
  }

  if (typeof error?.message === 'string' && error.message.trim()) {
    return error.message;
  }

  return fallbackMessage;
}
