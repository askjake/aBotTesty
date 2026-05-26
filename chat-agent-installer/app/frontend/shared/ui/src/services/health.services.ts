import axiosLibs from '@shared/ui/libs/axios.libs';

import { HealthType } from '@shared/ui/types/health.types';

export const getHealth = async (): Promise<HealthType> => {
  const { data } = await axiosLibs.get('/health');
  return data;
};
