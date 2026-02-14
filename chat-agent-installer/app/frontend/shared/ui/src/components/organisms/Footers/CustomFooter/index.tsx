import dynamic from 'next/dynamic';

import { StyledCustomFooter } from '@shared/ui/components/organisms/Footers/CustomFooter/CustomFooter.styled';
import ContactBlock from '@shared/ui/components/molecules/Footer/ContactBlock';
import { Skeleton } from 'antd';
const ReleaseModal = dynamic(
  () => import('@shared/ui/components/molecules/Modals/ReleaseModal'),
  {
    ssr: false,
  },
);
const HealthBlock = dynamic(
  () => import('@shared/ui/components/molecules/Footer/HealthBlock'),
  {
    ssr: false,
    loading: () => (
      <Skeleton.Button
        active
        style={{ height: '24px', width: '86px', display: 'block' }}
      />
    ),
  },
);

const CustomFooter = () => {
  return (
    <StyledCustomFooter data-testid='custom-footer' className='custom-footer'>
      <HealthBlock />
      <ContactBlock />
      <ReleaseModal />
    </StyledCustomFooter>
  );
};

export default CustomFooter;
