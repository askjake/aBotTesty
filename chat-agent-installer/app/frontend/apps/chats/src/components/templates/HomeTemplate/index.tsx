import { Flex, Spin } from 'antd';
import dynamic from 'next/dynamic';

import { StyledHomeLayout } from '@/components/templates/HomeTemplate/HomeTemplate.styled';
import ContainerWithSidebar from '@/components/containers/ContainerWithSidebar';

const Chat = dynamic(() => import('@/components/organisms/Chat'), {
  loading: () => (
    <Flex align='center' justify='center' style={{ height: '100vh' }}>
      <Spin />
    </Flex>
  ),
});

const HomeTemplate = () => {
  return (
    <ContainerWithSidebar showChats>
      <StyledHomeLayout>
        <Chat />
      </StyledHomeLayout>
    </ContainerWithSidebar>
  );
};

export default HomeTemplate;
