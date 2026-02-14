import { IssueCandidatesProps } from '@/types/beta-reports.types';
import { CardProps } from 'antd';
import { RefObject } from 'react';

export interface ActiveIssuesRef {
  refetchData: () => Promise<void>;
}

export type ActiveIssuesProps = IssueCandidatesProps &
  CardProps & {
    componentRef: RefObject<ActiveIssuesRef | null>;
  };
