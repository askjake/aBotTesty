import { MailOutlined } from '@ant-design/icons';

import { StyledContactBlock } from '@shared/ui/components/molecules/Footer/ContactBlock/ContactBlock.styled';
import { CONTACT_EMAIL } from '@shared/ui/constants/common.constants';

const ContactBlock = () => {
  return (
    <StyledContactBlock
      href={`https://mail.google.com/mail/u/0/?su=Question&to=${CONTACT_EMAIL}&tf=cm`}
      target='_blank'
    >
      <MailOutlined />
      <span>Send us feedback</span>
    </StyledContactBlock>
  );
};

export default ContactBlock;
