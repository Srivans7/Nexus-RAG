import httpClient from './httpClient';

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('original_file', file);

  const response = await httpClient.post('/api/upload/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

export async function processDocument(documentId) {
  const response = await httpClient.post(`/api/process/${documentId}/`);
  return response.data;
}
