import { FC, useState } from 'react';
import { App, Input, Modal } from 'antd';
const { TextArea } = Input;

import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { leaveFeedbackIssue } from '@/services/beta-reports.services';

import { FeedbackActiveIssueModalProps } from './FeedbackActiveIssueModal.props';

const FeedbackActiveIssueModal: FC<FeedbackActiveIssueModalProps> = ({
  id,
  accepted,
  className = '',
  onCancelFeedback,
  onSubmitFeedback,
  ...props
}) => {
  const { message } = App.useApp();
  const handleError = useHandleError();
  const [comments, setComments] = useState('');
  const [loading, setLoading] = useState(false);

  const handleOk = async () => {
    try {
      setLoading(true);
      await leaveFeedbackIssue({
        id,
        accepted: accepted as boolean,
        comments,
      });
      onSubmitFeedback();
      setComments('');
      message.success('Feedback submitted successfully');
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    onCancelFeedback();
    setComments('');
  };

  return (
    <Modal
      title='Leave your feedback'
      okText='Accept feedback'
      className={`feedback-issue-modal ${className}`}
      onOk={handleOk}
      onCancel={handleCancel}
      loading={loading}
      centered
      {...props}
    >
      <TextArea
        value={comments}
        onChange={(e) => setComments(e?.target?.value)}
        placeholder='Feedback...'
        autoSize={{ minRows: 2, maxRows: 6 }}
      />
    </Modal>
  );
};

export default FeedbackActiveIssueModal;
