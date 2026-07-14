// вызовы к бэкенду
import axios, { AxiosError } from 'axios';

const API_URL = 'http://localhost:8000'; 

export async function sendQuestion(question: string, history: any[], ticketId?: number) {
  try {
    const response = await axios.post(`${API_URL}/chat`, { question, history , ticketId});
    return response.data; // { answer, sources }
  } catch (error) {
    console.error('Error in sendQuestion:', error);
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError;
      console.error('Axios error details:', {
        message: axiosError.message,
        code: axiosError.code,
        status: axiosError.response?.status,
        data: axiosError.response?.data,
      });
    } else {
      console.error('Non-Axios error:', error);
    }
    throw error; // re-throw so the calling code can handle it
  }
}

export async function sendFeedback(question: string, answer: string, rating: number, history?: any[], comment?: string, ticketId?:number | null ) {
  try {
    if(ticketId){
      const response = await axios.post(`${API_URL}/feedback`, { question, answer, rating, comment, history ,ticketId});
      return response.data;
    }
    const response = await axios.post(`${API_URL}/feedback`, { question, answer, rating, comment, history });
    return response.data;
  } catch (error) {
    console.error('Error in sendFeedback:', error);
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError;
      console.error('Axios error details:', {
        message: axiosError.message,
        code: axiosError.code,
        status: axiosError.response?.status,
        data: axiosError.response?.data,
      });
    } else {
      console.error('Non-Axios error:', error);
    }
    throw error;
  }
}