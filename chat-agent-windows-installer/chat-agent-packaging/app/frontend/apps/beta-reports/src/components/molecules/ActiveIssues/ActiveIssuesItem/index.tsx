import { FC, useMemo } from 'react';
import { Button, Card, Flex, Tag, Tooltip } from 'antd';
import { DislikeOutlined, LikeOutlined } from '@ant-design/icons';

import { StyledActiveIssueText } from '@/components/organisms/ActiveIssues/ActiveIssues.styled';

import { ActiveIssueItemProps } from '@/components/molecules/ActiveIssues/ActiveIssuesItem/ActiveIssueItem.props';

const ActiveIssuesItem: FC<ActiveIssueItemProps> = ({
  id,
  platform,
  title = 'Issue without title',
  description,
  date,
  priority,
  accepted,
  onLeaveFeedback = () => {},
  className = '',
  ...props
}) => {
  const isAcceptedAvailable = useMemo(
    () => typeof accepted === 'boolean',
    [accepted],
  );
  const priorityLabel = useMemo(
    () => (priority === 0 ? 'Test Activity' : `P${priority}`),
    [priority],
  );
  return (
    <Card
      className={`active-issue-item ${className}`}
      title={
        <Tooltip title={title}>
          <span>{title}</span>
        </Tooltip>
      }
      extra={
        <Flex align='center' gap={4}>
          <Tooltip title='Leave a positive feedback'>
            <Button
              color='cyan'
              variant={isAcceptedAvailable && accepted ? 'solid' : 'text'}
              icon={<LikeOutlined />}
              onClick={() =>
                !isAcceptedAvailable && onLeaveFeedback({ accepted: true, id })
              }
            />
          </Tooltip>
          <Tooltip title='Leave a negative feedback'>
            <Button
              color='danger'
              variant={isAcceptedAvailable && !accepted ? 'solid' : 'text'}
              icon={<DislikeOutlined />}
              onClick={() =>
                !isAcceptedAvailable && onLeaveFeedback({ accepted: false, id })
              }
            />
          </Tooltip>
        </Flex>
      }
      {...props}
    >
      <Flex gap={6} vertical>
        <Flex align='center' gap={2}>
          <Tag bordered={false} color='processing'>
            {platform}
          </Tag>
          <Tag bordered={false} color='success'>
            {date}
          </Tag>
          <Tag bordered={false} color='error'>
            {priorityLabel}
          </Tag>
        </Flex>
        <StyledActiveIssueText
          ellipsis={{
            rows: 4,
            expandable: 'collapsible',
          }}
        >
          {description}
        </StyledActiveIssueText>
      </Flex>
    </Card>
  );
};

export default ActiveIssuesItem;
