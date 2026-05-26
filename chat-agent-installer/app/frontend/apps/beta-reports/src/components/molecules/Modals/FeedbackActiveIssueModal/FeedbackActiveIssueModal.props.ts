import { ModalProps } from 'antd';
import { IssueCandidateType } from '@/types/beta-reports.types';

export type FeedbackActiveIssueModalProps = ModalProps &
  Pick<IssueCandidateType, 'id' | 'accepted'> & {
    onSubmitFeedback: () => void;
    onCancelFeedback: () => void;
  };
