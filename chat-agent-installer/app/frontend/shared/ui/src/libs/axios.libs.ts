import axios from 'axios';
import {
  APP_ENV,
  BACKEND_URL,
  NODE_ENV,
} from '@shared/ui/constants/env.constants';
import { isServer } from '@shared/ui/constants/common.constants';

const axiosLibs = axios.create({
  baseURL: BACKEND_URL,
  withCredentials: true,
});

if (APP_ENV === 'local' && NODE_ENV !== 'production' && !isServer) {
  axiosLibs.interceptors.request.use(
    async (config) => {
      config.headers['X-Auth-Request-Email'] = 'test.test@dish.com';
      return config;
    },
    (error) => {
      return Promise.reject(error);
    },
  );
}

axiosLibs.interceptors.response.use(
  function (response) {
    return response;
  },
  async function (error) {
    return Promise.reject(error);
  },
);

export default axiosLibs;
