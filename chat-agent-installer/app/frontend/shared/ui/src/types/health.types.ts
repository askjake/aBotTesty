import { HealthStatusEnum } from '@shared/ui/enums/health.enums';

export type HealthType = {
  status: HealthStatusEnum;
  version: string;
  timestamp: string;
};
