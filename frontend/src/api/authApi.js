import axiosClient from './axiosClient';

export const login = async (studentId, password) => {
  const response = await axiosClient.post('/auth/login', { student_id: studentId, password });
  return response.data;
};
