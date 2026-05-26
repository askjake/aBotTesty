import { BetaReportsProps } from '@/types/beta-reports.types';
import { CardProps } from 'antd';
import { RefObject } from 'react';

export interface ReportsRef {
  refetchData: () => Promise<void>;
}

export type ReportsProps = BetaReportsProps &
  CardProps & {
    componentRef: RefObject<ReportsRef | null>;
  };
