import { FC, useEffect, useState } from 'react';
import { Col, Divider, Drawer, Row, Statistic, Typography } from 'antd';
const { Title } = Typography;

import customDayjs from '@shared/ui/libs/dayjs.libs';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import {
  getChatsUsageByRange,
  getChatUsage,
} from '@shared/ui/services/chats.services';
import { useAppSelector } from '@shared/ui/store';

import { ChatInfoDrawerProps } from '@/components/molecules/Drawers/ChatInfoDrawer/ChatInfoDrawer.props';
import { ChatUsageType } from '@shared/ui/types/chats.types';
import { StyledChatInfoDrawerBlock } from '@/components/molecules/Drawers/ChatInfoDrawer/ChatInfoDrawer.styled';

const ChatInfoDrawer: FC<ChatInfoDrawerProps> = (props) => {
  const handleError = useHandleError();
  const activeChat = useAppSelector((store) => store.chats.activeChat);
  const [chatInfo, setChatInfo] = useState<null | ChatUsageType>(null);
  const [chatsInfo, setChatsInfo] = useState<null | ChatUsageType>(null);
  const [loading, setLoading] = useState(true);
  const getData = async () => {
    try {
      setLoading(true);
      setChatsInfo(
        await getChatsUsageByRange({
          start_date: customDayjs().subtract(30, 'days').toDate(),
          end_date: customDayjs().toDate(),
        }),
      );
      if (activeChat?.chat_id) {
        setChatInfo(await getChatUsage(activeChat?.chat_id));
      } else {
        setChatInfo(null);
      }
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    getData();
  }, [activeChat]);
  return (
    <Drawer
      {...props}
      placement='right'
      title='Chat information'
      loading={loading}
    >
      {chatsInfo ? (
        <StyledChatInfoDrawerBlock>
          <Title level={4}>Total usage in last 30 days</Title>
          <Divider />
          <Row gutter={16}>
            <Col span={12}>
              <Statistic
                title='Total input tokens'
                value={chatsInfo?.input_token?.toFixed(0)}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title='Total output tokens'
                value={chatsInfo?.output_token?.toFixed(0)}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title='Total cost'
                value={`$${chatsInfo?.cost?.toFixed(2)}`}
              />
            </Col>
          </Row>
        </StyledChatInfoDrawerBlock>
      ) : null}
      {chatInfo ? (
        <StyledChatInfoDrawerBlock>
          <Title level={4}>Total usage by current chat</Title>
          <Divider />
          <Row gutter={16}>
            <Col span={12}>
              <Statistic
                title='Total input tokens'
                value={chatInfo?.input_token?.toFixed(0)}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title='Total output tokens'
                value={chatInfo?.output_token?.toFixed(0)}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title='Total cost'
                value={`$${chatInfo?.cost?.toFixed(2)}`}
              />
            </Col>
          </Row>
        </StyledChatInfoDrawerBlock>
      ) : null}
    </Drawer>
  );
};

export default ChatInfoDrawer;
