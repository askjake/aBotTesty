import { FC, useEffect, useImperativeHandle, useState } from 'react';
import { Empty, Spin } from 'antd';
import { RedoOutlined } from '@ant-design/icons';
import InfiniteScroll from 'react-infinite-scroll-component';
import dynamic from 'next/dynamic';

import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { getIssueCandidates } from '@/services/beta-reports.services';

import ActiveIssuesItem from '@/components/molecules/ActiveIssues/ActiveIssuesItem';
import { StyledActiveIssues } from '@/components/organisms/ActiveIssues/ActiveIssues.styled';
const FeedbackIssueModal = dynamic(
  () => import('@/components/molecules/Modals/FeedbackActiveIssueModal'),
  {
    ssr: false,
  },
);

import { IssueCandidateType } from '@/types/beta-reports.types';
import { ActiveIssuesProps } from '@/components/organisms/ActiveIssues/ActiveIssues.props';

const ActiveIssues: FC<ActiveIssuesProps> = ({
  className = '',
  start_date,
  end_date,
  platform,
  release,
  min_priority,
  componentRef,
  ...props
}) => {
  const [loading, setLoading] = useState(false);
  const [issues, setIssues] = useState<IssueCandidateType[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [hasMorePages, setHasMorePages] = useState(false);
  const [feedbackModal, setFeedbackModal] = useState<
    { open: boolean } & Pick<IssueCandidateType, 'id' | 'accepted'>
  >({
    open: false,
    accepted: false,
    id: '',
  });
  const handleError = useHandleError();
  useImperativeHandle(
    componentRef,
    () => ({
      refetchData: async () => {
        await handleLoadMore(true);
      },
    }),
    [],
  );

  const handleLoadMore = async (isReset = false) => {
    try {
      if (loading) {
        return;
      }
      const nextPage = isReset ? 1 : currentPage + 1;
      if (nextPage === 1) {
        setLoading(true);
      }
      const { docs = [], hasNextPage = false } = await getIssueCandidates({
        page: nextPage,
        limit: 15,
        platform,
        release,
        min_priority,
        max_priority: min_priority,
        start_date,
        end_date,
      });
      setHasMorePages(hasNextPage);
      setIssues((prev) => [...(!isReset && nextPage > 1 ? prev : []), ...docs]);
      setCurrentPage(nextPage);
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };

  const handleLeaveFeedback = ({
    accepted,
    id,
  }: Pick<IssueCandidateType, 'id' | 'accepted'>) => {
    setFeedbackModal({
      open: true,
      accepted,
      id,
    });
  };

  const handleSubmitFeedback = async () => {
    if (!feedbackModal?.open) return;
    setIssues((prev) =>
      prev.map((item) => ({
        ...item,
        ...(item.id === feedbackModal?.id && {
          accepted: feedbackModal?.accepted,
        }),
      })),
    );
    setFeedbackModal((prev) => ({
      ...prev,
      open: false,
      id: '',
    }));
  };

  const handleCancelFeedback = async () => {
    if (!feedbackModal?.open) return;
    setFeedbackModal((prev) => ({
      ...prev,
      open: false,
      id: '',
    }));
  };

  useEffect(() => {
    if (release) {
      setIssues([]);
      setCurrentPage(0);
      setHasMorePages(false);
      handleLoadMore(true);
    }
  }, [start_date, end_date, platform, release, min_priority]);

  return (
    <StyledActiveIssues
      title='Active issues'
      className={`active-issues ${className}`}
      loading={loading}
      id='active-issues-wrapper'
      {...props}
    >
      {!issues.length ? (
        <Empty />
      ) : (
        <InfiniteScroll
          dataLength={issues.length}
          next={handleLoadMore}
          hasMore={hasMorePages}
          loader={
            <div style={{ textAlign: 'center' }}>
              <Spin indicator={<RedoOutlined spin />} size='small' />
            </div>
          }
          scrollableTarget='active-issues-wrapper'
        >
          {issues.map((item) => (
            <ActiveIssuesItem
              key={item.id}
              onLeaveFeedback={handleLeaveFeedback}
              {...item}
            />
          ))}
        </InfiniteScroll>
      )}
      <FeedbackIssueModal
        onSubmitFeedback={handleSubmitFeedback}
        onCancelFeedback={handleCancelFeedback}
        {...feedbackModal}
      />
    </StyledActiveIssues>
  );
};

export default ActiveIssues;
