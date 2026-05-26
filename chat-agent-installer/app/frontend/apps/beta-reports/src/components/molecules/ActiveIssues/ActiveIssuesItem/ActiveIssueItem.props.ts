import { CardProps } from 'antd';
import { IssueCandidateType } from '@/types/beta-reports.types';

export type ActiveIssueItemProps = CardProps &
  IssueCandidateType & {
    onLeaveFeedback: ({
      accepted,
      id,
    }: Pick<IssueCandidateType, 'id' | 'accepted'>) => void;
  };
